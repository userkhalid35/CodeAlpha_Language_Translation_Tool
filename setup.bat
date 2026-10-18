@echo off
setlocal EnableDelayedExpansion

echo =======================================================
echo     CodeAlpha Language Translation Tool - Setup
echo =======================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "REQUIREMENTS_FILE=%SCRIPT_DIR%requirements.txt"

:: Step 1: Detect Python installation (prefer py -3.15, fallback to python)
echo [1/3] Detecting Python installation...

set PYTHON_CMD=

:: Check for py -3.15
py -3.15 -c "import sys; sys.exit(0)" >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    set "PYTHON_CMD=py -3.15"
    goto :python_detected
)

:: Check for py launcher
py -3 -c "import sys; sys.exit(0)" >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    set "PYTHON_CMD=py -3"
    goto :python_detected
)

:: Check for standard python executable
python -c "import sys; sys.exit(0)" >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    set "PYTHON_CMD=python"
    goto :python_detected
)

:python_not_found
echo.
echo [ERROR] Python was not found on your system!
echo Please install Python 3.15 (64-bit) from https://www.python.org/downloads/
echo Make sure to check "Add python.exe to PATH" during installation.
echo.
exit /b 1

:python_detected
for /f "delims=" %%I in ('!PYTHON_CMD! -c "import sys; print(sys.version.split()[0])"') do set "DETECTED_VER=%%I"
echo Found: Python %DETECTED_VER% using [%PYTHON_CMD%]
echo.

:: Step 2: Create local virtual environment (.venv) if needed
echo [2/3] Configuring virtual environment (.venv)...
if exist "%VENV_PYTHON%" (
    echo Existing virtual environment detected at:
    echo   %VENV_DIR%
) else (
    echo Creating fresh virtual environment at:
    echo   %VENV_DIR%
    !PYTHON_CMD! -m venv "%VENV_DIR%"
    if !ERRORLEVEL! NEQ 0 (
        echo.
        echo [ERROR] Failed to create virtual environment!
        exit /b 1
    )
)
echo.

:: Step 3: Upgrade pip and install dependencies
echo [3/3] Installing dependencies from requirements.txt...
if not exist "%REQUIREMENTS_FILE%" (
    echo.
    echo [ERROR] requirements.txt not found at: %REQUIREMENTS_FILE%
    exit /b 1
)

"%VENV_PYTHON%" -m pip install --upgrade pip
if !ERRORLEVEL! NEQ 0 (
    echo [WARNING] Could not upgrade pip. Continuing with installation...
)

"%VENV_PYTHON%" -m pip install -r "%REQUIREMENTS_FILE%"
if !ERRORLEVEL! NEQ 0 (
    echo.
    echo [ERROR] Failed to install dependencies!
    echo Please check your internet connection and retry.
    exit /b 1
)

echo.
echo =======================================================
echo     Setup Successful! Ready to launch.
echo =======================================================
echo To launch the application, run:
echo     run.bat
echo or:
echo     .\run.bat
echo.
exit /b 0
