@echo off
setlocal EnableExtensions DisableDelayedExpansion

if /i "%~1"=="build" goto verify_stdlib
if /i "%~1"=="typecheck" goto verify_stdlib
if /i "%~1"=="test" goto verify_stdlib
goto run_grill

:verify_stdlib
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Verify-StdlibSource.ps1"
if errorlevel 1 exit /b 1

:run_grill
rem Use the existing installation without depending on its launcher exit codes.
if not defined WURST_TOOLCHAIN_HOME set "WURST_TOOLCHAIN_HOME=%USERPROFILE%\.wurst"
set "GRILL_JAVA=%WURST_TOOLCHAIN_HOME%\wurst-runtime\bin\java.exe"
set "GRILL_JAR=%WURST_TOOLCHAIN_HOME%\grill-cli\grill.jar"
if not exist "%GRILL_JAVA%" (
	echo Missing Wurst Java runtime: "%GRILL_JAVA%"
	exit /b 1
)
if not exist "%GRILL_JAR%" (
	echo Missing Grill JAR: "%GRILL_JAR%"
	exit /b 1
)

rem Isolate the reviewed legacy compiler from the user's global/default compiler.
if not defined WURST_LEGACY_INSTALL_DIR set "WURST_LEGACY_INSTALL_DIR=E:\WurstToolchain\legacy-jass-8192"
if /i "%~1"=="build" goto verify_compiler
if /i "%~1"=="typecheck" goto verify_compiler
if /i "%~1"=="test" goto verify_compiler
goto launch_grill

:verify_compiler
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0compiler\Verify-LegacyCompiler.ps1" -InstallDir "%WURST_LEGACY_INSTALL_DIR%" -GrillJar "%GRILL_JAR%"
if errorlevel 1 exit /b 1
"%WURST_TOOLCHAIN_HOME%\wurst-jdk\bin\java.exe" "-Dwurst.install.dir=%WURST_LEGACY_INSTALL_DIR%" -cp "%GRILL_JAR%" "%~dp0compiler\ProbeCompilerLaunch.java" "%WURST_LEGACY_INSTALL_DIR%\wurst-compiler\wurstscript.jar"
if errorlevel 1 exit /b 1

:launch_grill

for /f "tokens=2 delims=:" %%A in ('chcp') do for /f "tokens=1" %%B in ("%%A") do set "GRILL_OLD_CP=%%B"
chcp 65001 >nul
"%GRILL_JAVA%" "-Dwurst.install.dir=%WURST_LEGACY_INSTALL_DIR%" -Dfile.encoding=UTF-8 --enable-native-access=ALL-UNNAMED -jar "%GRILL_JAR%" %*
set "GRILL_RESULT=%ERRORLEVEL%"
rem CMD callers use errorlevel 1; normalize Windows exception exit codes.
if %GRILL_RESULT% LSS 0 set "GRILL_RESULT=1"
if defined GRILL_OLD_CP chcp %GRILL_OLD_CP% >nul
endlocal & exit /b %GRILL_RESULT%
