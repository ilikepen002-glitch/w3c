param(
	[ValidateSet("Stage", "StageNative", "Clean")]
	[string] $Mode = "Stage",
	[string] $NativeTest = $env:WURST_NATIVE_PLAYTEST
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$sourceDir = Join-Path $repoRoot "tests\\wurst"
$stageDir = Join-Path $repoRoot "wurst\\_tests"

function Remove-StageDir() {
	if (Test-Path -LiteralPath $stageDir) {
		$resolvedStage = (Resolve-Path -LiteralPath $stageDir).Path
		$expectedStage = [System.IO.Path]::GetFullPath((Join-Path $repoRoot 'wurst\_tests'))
		if ($resolvedStage -ne $expectedStage) { throw "Unexpected Wurst staging path: $resolvedStage" }
		Remove-Item -LiteralPath $resolvedStage -Recurse -Force
	}
}

if ($Mode -eq "Clean") {
	Remove-StageDir
	exit 0
}

Remove-StageDir
if ($Mode -eq 'StageNative') {
	if ($NativeTest -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
		throw 'NativeTest must be a package base name, without a path or extension.'
	}
	$runtimeRoot = [System.IO.Path]::GetFullPath((Join-Path $sourceDir 'runtime'))
	$nativeSource = Join-Path $runtimeRoot ($NativeTest + '.wurst')
	if (-not (Test-Path -LiteralPath $nativeSource -PathType Leaf)) {
		throw "Native test source not found: $nativeSource"
	}
	$nativeFile = Get-Item -LiteralPath $nativeSource
	if ($nativeFile.DirectoryName -ne $runtimeRoot -or $nativeFile.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
		throw 'Native test must be a regular file directly inside tests/wurst/runtime.'
	}
	try {
		New-Item -ItemType Directory -Path $stageDir -Force | Out-Null
		Copy-Item -LiteralPath $nativeSource -Destination (Join-Path $stageDir $nativeFile.Name) -Force
	} catch {
		Remove-StageDir
		throw
	}
	exit 0
}
New-Item -ItemType Directory -Path $stageDir -Force | Out-Null

if (-not (Test-Path -LiteralPath $sourceDir)) {
	exit 0
}

$sourceRoot = (Resolve-Path $sourceDir).Path
Get-ChildItem -LiteralPath $sourceRoot -Recurse -File -Filter *.wurst | ForEach-Object {
	$relativePath = $_.FullName.Substring($sourceRoot.Length).TrimStart("\\")
	$targetPath = Join-Path $stageDir $relativePath
	$targetDir = Split-Path -Parent $targetPath
	if (-not (Test-Path -LiteralPath $targetDir)) {
		New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
	}
	Copy-Item -LiteralPath $_.FullName -Destination $targetPath -Force
}
