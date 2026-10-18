@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "VENV_PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe"
set "MAIN_SCRIPT=%SCRIPT_DIR%main.py"

:: Check if virtual environment exists; run setup if missing
if not exist "%VENV_PYTHON%" (
    echo =======================================================
    echo  Virtual environment (.venv) not found.
    echo  Running setup.bat to configure dependencies...
    echo =======================================================
    echo.
    call "%SCRIPT_DIR%setup.bat"
    if errorlevel 1 (
        echo.
        echo [ERROR] Setup failed. Cannot launch application.
        exit /b 1
    )
)

:: Launch the desktop application directly without console lag
"%VENV_PYTHON%" "%MAIN_SCRIPT%" %*
exit /b %ERRORLEVEL%
