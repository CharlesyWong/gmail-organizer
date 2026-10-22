@echo off
setlocal
pushd "%~dp0.." || exit /b 4
if not exist "logs" mkdir "logs"
set "PYTHONUTF8=1"

set "PYTHON=.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

if "%~1"=="" (
    set "ARGS=--apply"
) else (
    set "ARGS=%*"
)

"%PYTHON%" -m gmail_organizer run %ARGS% >> "logs\task.log" 2>&1
set "RC=%ERRORLEVEL%"
popd
exit /b %RC%
