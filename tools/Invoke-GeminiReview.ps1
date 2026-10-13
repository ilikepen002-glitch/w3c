[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Task,

    [ValidateSet("implementation", "proposal")]
    [string]$ReviewKind = "implementation",

    [string[]]$Files = @(),

    [string]$BaseRef = "HEAD",

    [string]$TestSummary = "",

    [string]$Notes = "",

    [string]$Model = "gemini-2.5-flash",

    [ValidateSet("text", "json")]
    [string]$OutputFormat = "text",

    [string]$OutputFile = "",

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Limit-Text {
    param(
        [AllowNull()]
        [string]$Text,
        [int]$MaxChars,
        [string]$Label
    )

    if ([string]::IsNullOrWhiteSpace($Text)) {
        return "(no $Label available)"
    }

    if ($Text.Length -le $MaxChars) {
        return $Text
    }

    $remaining = $Text.Length - $MaxChars
    return $Text.Substring(0, $MaxChars) + "`n... [truncated $remaining chars from $Label]"
}

function Get-GitOutput {
    param(
        [string[]]$GitArgs
    )

    $previousNativePreference = $PSNativeCommandUseErrorActionPreference
    $PSNativeCommandUseErrorActionPreference = $false
    try {
        $rawResult = & git -c core.safecrlf=false -c core.autocrlf=false @GitArgs 2>&1
        $exitCode = $LASTEXITCODE
    } finally {
        $PSNativeCommandUseErrorActionPreference = $previousNativePreference
    }

    $result = $rawResult | Where-Object {
        $_.ToString() -notmatch "^warning: LF will be replaced by CRLF in "
    }

    if ($exitCode -ne 0) {
        return ""
    }
    return ($result | Out-String).TrimEnd()
}

function Quote-ProcessArg {
    param(
        [string]$Value
    )

    if ($null -eq $Value) {
        return '""'
    }

    if ($Value -match '[\s"]') {
        return '"' + ($Value -replace '"', '\"') + '"'
    }

    return $Value
}

function Convert-JsonToAscii {
    param(
        [string]$JsonText
    )

    if ($null -eq $JsonText) {
        return ""
    }

    $builder = New-Object System.Text.StringBuilder
    foreach ($char in $JsonText.ToCharArray()) {
        $codePoint = [int][char]$char
        if ($codePoint -le 0x7F) {
            [void]$builder.Append($char)
        } else {
            [void]$builder.AppendFormat("\u{0:x4}", $codePoint)
        }
    }

    return $builder.ToString()
}

$useGeminiApi = -not [string]::IsNullOrWhiteSpace($env:GEMINI_API_KEY)
$geminiNodePath = $null
$geminiEntryPath = $null

if (-not $useGeminiApi) {
    if (-not (Get-Command gemini -ErrorAction SilentlyContinue)) {
        throw "Gemini CLI was not found in PATH, and GEMINI_API_KEY is not set."
    }

    $geminiCommand = Get-Command gemini -ErrorAction Stop
    $geminiBaseDir = Split-Path $geminiCommand.Source -Parent
    $geminiNodePath = Join-Path $geminiBaseDir "node.exe"
    $geminiEntryPath = Join-Path $geminiBaseDir "node_modules/@google/gemini-cli/bundle/gemini.js"

    if (-not (Test-Path $geminiEntryPath)) {
        throw "Gemini CLI entry file was not found at $geminiEntryPath"
    }

    if (-not (Test-Path $geminiNodePath)) {
        $geminiNodePath = "node.exe"
    }
}

$repoRoot = Get-GitOutput -GitArgs @("rev-parse", "--show-toplevel")
if ([string]::IsNullOrWhiteSpace($repoRoot)) {
    throw "Invoke-GeminiReview.ps1 must run inside a git repository."
}

$env:HTTP_PROXY = "http://127.0.0.1:7890"
$env:HTTPS_PROXY = "http://127.0.0.1:7890"
$env:NO_PROXY = "127.0.0.1,localhost"

$statusText = Get-GitOutput -GitArgs @("status", "--short")

$uniqueFiles = @()
if ($Files.Count -gt 0) {
    $uniqueFiles = $Files | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Sort-Object -Unique
} else {
    $diffNames = Get-GitOutput -GitArgs @("diff", "--name-only", $BaseRef)
    if (-not [string]::IsNullOrWhiteSpace($diffNames)) {
        $uniqueFiles = $diffNames -split "`r?`n" | Where-Object { $_ } | Sort-Object -Unique
    }
}

$pathArgs = @()
if ($uniqueFiles.Count -gt 0) {
    $pathArgs += "--"
    $pathArgs += $uniqueFiles
}

$diffStatArgs = @("diff", "--no-ext-diff", "--stat")
if (-not [string]::IsNullOrWhiteSpace($BaseRef)) {
    $diffStatArgs += $BaseRef
}
$diffStatArgs += $pathArgs
$diffStat = Get-GitOutput -GitArgs $diffStatArgs

$diffArgs = @("diff", "--no-ext-diff", "--unified=3")
if (-not [string]::IsNullOrWhiteSpace($BaseRef)) {
    $diffArgs += $BaseRef
}
$diffArgs += $pathArgs
$diffText = Get-GitOutput -GitArgs $diffArgs

if ([string]::IsNullOrWhiteSpace($diffText)) {
    $cachedDiffArgs = @("diff", "--cached", "--no-ext-diff", "--unified=3")
    $cachedDiffArgs += $pathArgs
    $diffText = Get-GitOutput -GitArgs $cachedDiffArgs
}

$changedFilesBlock = if ($uniqueFiles.Count -gt 0) {
    ($uniqueFiles | ForEach-Object { "- $_" }) -join "`n"
} else {
    "- (no changed files auto-detected)"
}

$reviewSpecificInstructions = if ($ReviewKind -eq "proposal") {
@"
Proposal review expectations:
- Treat Task, Changed files, Validation summary, and Additional notes as the proposed implementation plan.
- Review whether the approach targets the right source files, stays out of generated outputs, is appropriately scoped, and has a credible validation plan.
- If there is no diff yet, that is expected. Do not treat the lack of code changes as a problem by itself.
- Challenge weak assumptions, risky sequencing, missing alternatives, and gaps between the stated goal and the proposed approach.
"@
} else {
@"
Implementation review expectations:
- Review the actual code changes and validation evidence for defects, regressions, missing tests, and build or gameplay risk.
- Use the diff as primary evidence and call out when the validation summary does not adequately cover the touched behavior.
"@
}

$reviewPriorityInstruction = if ($ReviewKind -eq "proposal") {
    "- Prioritize plan flaws, risky assumptions, wrong file targeting, missing validation, and over- or under-scoping over style-only commentary."
} else {
    "- Prioritize real defects, regression risk, and missing validation over style-only commentary."
}

$prompt = @"
You are ReviewAgent for a Warcraft III WurstScript map project.

Review kind: $ReviewKind
Task:
$Task

Repository constraints:
- Source of truth is Wurst source, not _build, _build/dependencies, or generated war3map.j.
- The map currently uses scriptMode: JASS and wc3Patch: v1.28.
- Standard validation uses tools\Run-WurstChecks.bat.
- Build-sensitive validation uses build-and-deploy-test-map.bat.
- Focus on gameplay correctness, initialization order, compiletime object generation safety, rawcode and upgrade-chain consistency, test adequacy, and regression risk.

$reviewSpecificInstructions

Changed files:
$changedFilesBlock

Git status:
$statusText

Validation summary:
$TestSummary

Additional notes:
$Notes

Diff stat:
$(Limit-Text -Text $diffStat -MaxChars 4000 -Label "diff stat")

Unified diff (may be empty for proposal reviews):
$(Limit-Text -Text $diffText -MaxChars 40000 -Label "diff")

Output requirements:
- Start with exactly one verdict line:
  VERDICT: PASS
  VERDICT: PASS WITH NOTES
  VERDICT: FAIL
- Then write these sections in order:
  Findings:
  Risks:
  Suggested follow-up:
$reviewPriorityInstruction
- If context is insufficient, state what is missing instead of inventing facts.
"@

if ($DryRun) {
    $prompt | Write-Output
    return
}

$apiUri = "https://generativelanguage.googleapis.com/v1beta/models/$($Model):generateContent"

if ($useGeminiApi) {
    $requestBody = @{
        contents = @(
            @{
                role = "user"
                parts = @(
                    @{
                        text = $prompt
                    }
                )
            }
        )
        generationConfig = @{
            temperature = 0
            maxOutputTokens = 4096
        }
    } | ConvertTo-Json -Depth 8
    $requestBody = Convert-JsonToAscii $requestBody

    try {
        $apiResponse = Invoke-RestMethod `
            -Uri $apiUri `
            -Method Post `
            -Headers @{ "x-goog-api-key" = $env:GEMINI_API_KEY } `
            -ContentType "application/json" `
            -Body $requestBody `
            -Proxy $env:HTTP_PROXY `
            -TimeoutSec 180
    } catch {
        $errorText = $_.ToString()
        if ($_.ErrorDetails -and -not [string]::IsNullOrWhiteSpace($_.ErrorDetails.Message)) {
            $errorText += "`n" + $_.ErrorDetails.Message
        } elseif ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $errorBody = $reader.ReadToEnd()
            if (-not [string]::IsNullOrWhiteSpace($errorBody)) {
                $errorText += "`n" + $errorBody
            }
        }
        throw "Gemini API review command failed.`n$errorText"
    }

    if ($OutputFormat -eq "json") {
        $rawText = $apiResponse | ConvertTo-Json -Depth 20
    } else {
        $rawText = (
            $apiResponse.candidates |
            ForEach-Object { $_.content.parts } |
            ForEach-Object { $_ } |
            ForEach-Object { $_.text }
        ) -join ""
    }

    if ($OutputFile) {
        Set-Content -Path $OutputFile -Value $rawText -Encoding UTF8
    }

    $rawText | Write-Output
    return
}

$sessionId = [guid]::NewGuid().ToString()

$geminiArgs = @(
    $geminiEntryPath,
    "--prompt=",
    "--model", $Model,
    "--skip-trust",
    "--session-id", $sessionId,
    "--output-format", $OutputFormat,
    "--approval-mode", "plan"
)

$startInfo = [System.Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = $geminiNodePath
$startInfo.UseShellExecute = $false
$startInfo.RedirectStandardInput = $true
$startInfo.RedirectStandardOutput = $true
$startInfo.RedirectStandardError = $true
$startInfo.CreateNoWindow = $true

$startInfo.Arguments = ($geminiArgs | ForEach-Object { Quote-ProcessArg $_ }) -join " "

$startInfo.EnvironmentVariables["HTTP_PROXY"] = $env:HTTP_PROXY
$startInfo.EnvironmentVariables["HTTPS_PROXY"] = $env:HTTPS_PROXY
$startInfo.EnvironmentVariables["NO_PROXY"] = $env:NO_PROXY

$process = [System.Diagnostics.Process]::new()
$process.StartInfo = $startInfo
[void]$process.Start()
$process.StandardInput.Write($prompt)
$process.StandardInput.Close()

$stdoutText = $process.StandardOutput.ReadToEnd()
$stderrText = $process.StandardError.ReadToEnd()
$process.WaitForExit()

$exitCode = $process.ExitCode
$rawText = (($stdoutText + "`n" + $stderrText).Trim())

if ($OutputFile) {
    Set-Content -Path $OutputFile -Value $rawText -Encoding UTF8
}

if ($exitCode -ne 0) {
    if ($rawText -match "IneligibleTierError|UNSUPPORTED_LOCATION|not eligible") {
        throw "Gemini CLI is installed but not currently authenticated for usable review in this environment.`n$rawText"
    }
    throw "Gemini review command failed.`n$rawText"
}

$rawText | Write-Output
