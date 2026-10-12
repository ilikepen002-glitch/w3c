param([string]$Source = 'E:/WurstToolchain/WurstScript-source', [string]$InstallDir = 'E:/WurstToolchain/legacy-jass-8192', [string]$ToolchainHome = "$env:USERPROFILE/.wurst")
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Get-Sha256.ps1')
$lock = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'compiler-lock.json') -Raw | ConvertFrom-Json
$jar = Join-Path $Source 'de.peeeq.wurstscript/build/libs/wurstscript.jar'
if ((Get-CompilerSha256 $jar) -ne $lock.compilerSha256) { throw 'Built compiler jar differs from the reviewed lock.' }
$compilerDir = Join-Path $InstallDir 'wurst-compiler'
New-Item -ItemType Directory -Path $compilerDir -Force | Out-Null
Copy-Item -LiteralPath $jar -Destination (Join-Path $compilerDir 'wurstscript.jar') -Force
$runtime = Join-Path $InstallDir 'wurst-runtime'
if (-not (Test-Path -LiteralPath $runtime)) {
    New-Item -ItemType Junction -Path $runtime -Target (Join-Path $ToolchainHome 'wurst-runtime') | Out-Null
}
& (Join-Path $PSScriptRoot 'Verify-LegacyCompiler.ps1') -InstallDir $InstallDir -GrillJar (Join-Path $ToolchainHome 'grill-cli/grill.jar')
