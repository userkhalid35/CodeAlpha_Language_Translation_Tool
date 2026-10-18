@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "VENV_PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe"
set "MAIN_SCRIPT=%SCRIPT_DIR%main.py"

echo =======================================================
echo   CodeAlpha Translation Tool - Setup and Launch
echo =======================================================
echo.

call "%SCRIPT_DIR%setup.bat"
if errorlevel 1 (
    echo.
    echo [ERROR] Setup failed. Cannot launch application.
    exit /b 1
)

echo Starting CodeAlpha Language Translation Tool...
"%VENV_PYTHON%" "%MAIN_SCRIPT%" %*
exit /b %ERRORLEVEL%
