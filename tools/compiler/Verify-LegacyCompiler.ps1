param([Parameter(Mandatory=$true)][string]$InstallDir, [Parameter(Mandatory=$true)][string]$GrillJar)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Get-Sha256.ps1')
$lock = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'compiler-lock.json') -Raw | ConvertFrom-Json
$compiler = Join-Path $InstallDir 'wurst-compiler/wurstscript.jar'
$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$config = Get-Content -LiteralPath (Join-Path $projectRoot 'wurst.build')
if ($config -notcontains 'scriptMode: JASS' -or $config -notcontains 'wc3Patch: v1.28') { throw 'The locked legacy compiler requires the reviewed JASS/v1.28 configuration.' }
$common = Get-Content -LiteralPath (Join-Path $projectRoot '_build/dependencies/WurstStdlib2-source/common.j') -Raw
if ($common -notmatch '(?m)^\s*constant\s+integer\s+JASS_MAX_ARRAY_SIZE\s*=\s*8192\s*$') { throw 'Legacy compiler requires common.j target capacity 8192.' }
foreach ($check in @(@{ Path=$compiler; Hash=$lock.compilerSha256 }, @{ Path=$GrillJar; Hash=$lock.grillSha256 }, @{ Path=(Join-Path $PSScriptRoot 'legacy-jass-array-capacity.patch'); Hash=$lock.sourcePatchSha256 })) {
    if (-not (Test-Path -LiteralPath $check.Path -PathType Leaf)) { throw "Missing locked tool: $($check.Path)" }
    $actual = Get-CompilerSha256 $check.Path
    if ($actual -ne $check.Hash) { throw "Tool SHA256 mismatch: $($check.Path). Rebuild/install the reviewed legacy compiler; do not update the lock to accept an unknown jar." }
}
Write-Host "Verified legacy Jass compiler: $compiler"
