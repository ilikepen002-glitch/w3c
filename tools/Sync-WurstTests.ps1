param(
	[ValidateSet("Stage", "Clean")]
	[string] $Mode = "Stage"
)

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$sourceDir = Join-Path $repoRoot "tests\\wurst"
$stageDir = Join-Path $repoRoot "wurst\\_tests"

function Remove-StageDir() {
	if (Test-Path -LiteralPath $stageDir) {
		Remove-Item -LiteralPath $stageDir -Recurse -Force
	}
}

if ($Mode -eq "Clean") {
	Remove-StageDir
	exit 0
}

Remove-StageDir
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
