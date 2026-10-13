@echo off
setlocal

cd /d "%~dp0\.."

rem Reject undeclared combat actives before test staging/compiler execution.
python tools\VerifyActiveCooldownContract.py --source-only
if errorlevel 1 exit /b 1

set "MODE=%~1"
if "%MODE%"=="" set "MODE=all"

powershell -NoProfile -ExecutionPolicy Bypass -File "tools\Sync-WurstTests.ps1" -Mode Stage
if errorlevel 1 (
	powershell -NoProfile -ExecutionPolicy Bypass -File "tools\Sync-WurstTests.ps1" -Mode Clean >nul
	exit /b 1
)

set "RESULT=0"

if /i "%MODE%"=="all" (
	call tools\Run-Grill.bat typecheck --quiet
	if errorlevel 1 (
		set "RESULT=1"
		goto cleanup
	)
	call tools\Run-Grill.bat test --quiet
	if errorlevel 1 set "RESULT=1"
	goto cleanup
)

if /i "%MODE%"=="typecheck" (
	call tools\Run-Grill.bat %*
	if errorlevel 1 set "RESULT=1"
	goto cleanup
)

if /i "%MODE%"=="test" (
	call tools\Run-Grill.bat %*
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
if errorlevel 1 set "RESULT=1"
exit /b %RESULT%
