@echo off
setlocal

cd /d "%~dp0"

set "TARGET_DIR=D:\War3_1.27a\Warcraft III Frozen Throne 1.27a publish\Maps\Test"
set "MAP_TIMESTAMP="
if not defined WURST_TOOLCHAIN_HOME set "WURST_TOOLCHAIN_HOME=%USERPROFILE%\.wurst"
set "PATCH_JAVA=%WURST_TOOLCHAIN_HOME%\wurst-jdk\bin\java.exe"
set "PATCH_JAVAC=%WURST_TOOLCHAIN_HOME%\wurst-jdk\bin\javac.exe"
if not exist "%PATCH_JAVA%" goto missing_patch_jdk
if not exist "%PATCH_JAVAC%" goto missing_patch_jdk
goto patch_jdk_ready

:missing_patch_jdk
echo Missing complete JDK for the map display-name patch.
echo Install a complete JDK 27 at "%WURST_TOOLCHAIN_HOME%\wurst-jdk".
pause
exit /b 1

:patch_jdk_ready

powershell -NoProfile -ExecutionPolicy Bypass -File "tools\Sync-WurstTests.ps1" -Mode Clean >nul
if errorlevel 1 (
	echo Failed to clean staged Wurst tests.
	pause
	exit /b 1
)

for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "Get-Date -Format 'HHmm'"`) do set "MAP_TIMESTAMP=%%F"
if not defined MAP_TIMESTAMP (
	echo Failed to generate the temporary map timestamp.
	pause
	exit /b 1
)

echo [1/3] Building map...
rem Grill's MPQ reader can normalize its input. Build a disposable copy so the
rem reviewed terrain mask and its checksum metadata stay reproducible.
if not exist "_build" mkdir "_build"
copy /y "maps\ExampleMap.source.w3x" "_build\ExampleMap.input.w3x" >nul
if errorlevel 1 (
	echo Failed to prepare a disposable build input.
	pause
	exit /b 1
)
if not defined WURST_NATIVE_PLAYTEST goto build_map
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\Sync-WurstTests.ps1" -Mode StageNative
if not errorlevel 1 goto native_staged
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\Sync-WurstTests.ps1" -Mode Clean >nul
echo Native test staging failed.
exit /b 1

:native_staged
set "MAP_TIMESTAMP=TEST-%MAP_TIMESTAMP%"

:build_map
call tools\Run-Grill.bat build "_build\ExampleMap.input.w3x" --quiet
set "BUILD_RESULT=%ERRORLEVEL%"
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\Sync-WurstTests.ps1" -Mode Clean >nul
if errorlevel 1 (
	echo Failed to clean staged Wurst tests after build.
	exit /b 1
)
if not "%BUILD_RESULT%"=="0" (
	echo Build failed.
	pause
	exit /b 1
)

set "SOURCE_MAP="
for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "$map = Get-ChildItem -LiteralPath '_build' -File | Where-Object { ($_.Name -like '*.w3x' -or $_.Name -like '*.w3x.w3x') -and $_.Name -ne 'ExampleMap.input.w3x' } | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName; if ($map) { $map } else { exit 1 }"`) do set "SOURCE_MAP=%%F"

if not defined SOURCE_MAP (
	echo Build finished, but no output map was found.
	echo Checked: _build\*.w3x*
	pause
	exit /b 1
)

echo [2/3] Patching map display name with timestamp %MAP_TIMESTAMP%...
"%PATCH_JAVAC%" -cp "%WURST_TOOLCHAIN_HOME%\wurst-compiler\wurstscript.jar" "tools\PatchMapDisplayName.java"
if errorlevel 1 (
	echo Failed to compile tools\PatchMapDisplayName.java.
	pause
	exit /b 1
)

"%PATCH_JAVA%" -cp "tools;%WURST_TOOLCHAIN_HOME%\wurst-compiler\wurstscript.jar" PatchMapDisplayName "%SOURCE_MAP%" "%MAP_TIMESTAMP%"
if errorlevel 1 (
	echo Failed to patch the built map display name.
	pause
	exit /b 1
)

rem Keep the repository root map as the packaged artifact, never the build input.
copy /y "%SOURCE_MAP%" "ExampleMap.w3x" >nul
if errorlevel 1 (
	echo Failed to publish the built map to ExampleMap.w3x.
	pause
	exit /b 1
)

echo [3/3] Copying "%SOURCE_MAP%"
for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "$sourceMap = '%SOURCE_MAP%'; (Get-Item -LiteralPath $sourceMap).LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss')"`) do set "SOURCE_TIME=%%F"
echo Source map time:
echo   %SOURCE_TIME%
set "COPY_TARGET="
for /f "usebackq delims=" %%F in (`powershell -NoProfile -Command "$ErrorActionPreference = 'Stop'; $sourceMap = '%SOURCE_MAP%'; $targetDir = '%TARGET_DIR%'; $mapBaseName = [string]([char]0x5951) + [char]0x7075 + [char]0x5B88 + [char]0x536B + [char]0x6218; if (-not (Test-Path -LiteralPath $targetDir)) { New-Item -ItemType Directory -Path $targetDir | Out-Null }; Get-ChildItem -LiteralPath $targetDir -File -Filter ($mapBaseName + '*.w3x') -ErrorAction SilentlyContinue | Remove-Item -Force; $targetName = $mapBaseName + '.w3x'; $targetMap = Join-Path $targetDir $targetName; Copy-Item -LiteralPath $sourceMap -Destination $targetMap -Force; if (-not (Test-Path -LiteralPath $targetMap)) { throw 'Target map was not created.' }; $targetMap"`) do set "COPY_TARGET=%%F"
if not defined COPY_TARGET (
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
