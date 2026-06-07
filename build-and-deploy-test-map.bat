@echo off
setlocal

cd /d "%~dp0"

set "TARGET_DIR=D:\War3_1.27a\Warcraft III Frozen Throne 1.27a publish\Maps\Test"

powershell -NoProfile -ExecutionPolicy Bypass -File "tools\Sync-WurstTests.ps1" -Mode Clean >nul
if errorlevel 1 (
	echo Failed to clean staged Wurst tests.
	pause
	exit /b 1
)

echo [1/3] Building map...
call grill build ExampleMap.w3x --quiet
if errorlevel 1 (
	echo Build failed.
	pause
	exit /b 1
)

set "SOURCE_MAP="
for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "$map = Get-ChildItem -LiteralPath '_build' -File | Where-Object { $_.Name -like '*.w3x' -or $_.Name -like '*.w3x.w3x' } | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName; if ($map) { $map } else { exit 1 }"`) do set "SOURCE_MAP=%%F"

if not defined SOURCE_MAP (
	echo Build finished, but no output map was found.
	echo Checked: _build\*.w3x*
	pause
	exit /b 1
)

echo [2/3] Copying "%SOURCE_MAP%"
for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "$sourceMap = '%SOURCE_MAP%'; (Get-Item -LiteralPath $sourceMap).LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss')"`) do set "SOURCE_TIME=%%F"
echo Source map time:
echo   %SOURCE_TIME%
set "COPY_TARGET="
for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "$ErrorActionPreference = 'Stop'; $sourceMap = '%SOURCE_MAP%'; $targetDir = '%TARGET_DIR%'; $targetName = [string]([char]0x6DF1) + [char]0x6E0A + [char]0x5B88 + [char]0x671B + '.w3x'; if (-not (Test-Path -LiteralPath $targetDir)) { New-Item -ItemType Directory -Path $targetDir | Out-Null }; $targetMap = Join-Path $targetDir $targetName; Copy-Item -LiteralPath $sourceMap -Destination $targetMap -Force; if (-not (Test-Path -LiteralPath $targetMap)) { throw 'Target map was not created.' }; $targetMap"`) do set "COPY_TARGET=%%F"
if errorlevel 1 (
	echo Copy failed.
	echo The target map is probably open in Warcraft III or World Editor.
	echo Close anything using this file and run the script again:
	echo   %TARGET_DIR%
	pause
	exit /b 1
)

for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "$targetMap = '%COPY_TARGET%'; (Get-Item -LiteralPath $targetMap).LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss')"`) do set "TARGET_TIME=%%F"

echo [3/3] Done.
echo Source map:
echo   %SOURCE_MAP%
echo Deployed to:
echo   %COPY_TARGET%
echo Target map time:
echo   %TARGET_TIME%
pause
