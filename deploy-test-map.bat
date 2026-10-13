@echo off
setlocal

set "SOURCE_MAP=%~dp0ExampleMap.w3x"
set "TARGET_DIR=D:\War3_1.27a\Warcraft III Frozen Throne 1.27a publish\Maps\Test"

rem Copy the already packaged map without building or modifying it.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference = 'Stop'; try { if (-not (Test-Path -LiteralPath $env:SOURCE_MAP -PathType Leaf)) { throw ('Source map not found: ' + $env:SOURCE_MAP) }; $mapName = [string]([char]0x5951) + [char]0x7075 + [char]0x5B88 + [char]0x536B + [char]0x6218 + '.w3x'; if (-not (Test-Path -LiteralPath $env:TARGET_DIR -PathType Container)) { New-Item -ItemType Directory -Path $env:TARGET_DIR -Force | Out-Null }; $targetMap = Join-Path $env:TARGET_DIR $mapName; Copy-Item -LiteralPath $env:SOURCE_MAP -Destination $targetMap -Force; Write-Host ('Deployed to: ' + $targetMap) } catch { Write-Error -ErrorRecord $_ -ErrorAction Continue; exit 1 }"
if errorlevel 1 (
    echo Copy failed. Check the source map and whether the target file is in use.
    if /i not "%~1"=="--no-pause" pause
    exit /b 1
)

echo Done.
if /i not "%~1"=="--no-pause" pause
exit /b 0
