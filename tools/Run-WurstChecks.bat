@echo off
setlocal

cd /d "%~dp0\.."

set "MODE=%~1"
if "%MODE%"=="" set "MODE=all"

powershell -NoProfile -ExecutionPolicy Bypass -File "tools\Sync-WurstTests.ps1" -Mode Stage
if errorlevel 1 exit /b 1

set "RESULT=0"

if /i "%MODE%"=="all" (
	call grill typecheck --quiet
	if errorlevel 1 (
		set "RESULT=1"
		goto cleanup
	)
	call grill test --quiet
	if errorlevel 1 set "RESULT=1"
	goto cleanup
)

if /i "%MODE%"=="typecheck" (
	shift
	call grill typecheck %*
	if errorlevel 1 set "RESULT=1"
	goto cleanup
)

if /i "%MODE%"=="test" (
	shift
	call grill test %*
	if errorlevel 1 set "RESULT=1"
	goto cleanup
)

echo Usage:
echo   tools\Run-WurstChecks.bat
echo   tools\Run-WurstChecks.bat typecheck [grill args]
echo   tools\Run-WurstChecks.bat test [filter]
set "RESULT=1"

:cleanup
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\Sync-WurstTests.ps1" -Mode Clean >nul
exit /b %RESULT%
