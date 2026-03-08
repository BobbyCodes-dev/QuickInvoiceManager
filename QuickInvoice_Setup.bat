@echo off
setlocal enabledelayedexpansion
title QuickInvoice - Setup ^& Launcher
color 0B

set "APP_DIR=%~dp0"
set "VENV_DIR=%APP_DIR%venv"
set "REQ_FILE=%APP_DIR%requirements.txt"
set "APP_FILE=%APP_DIR%invoice_app.py"
set "EXE_FILE=%APP_DIR%dist\QuickInvoice.exe"
set "HASH_FILE=%APP_DIR%.last_build_hash"

echo.
echo  ============================================
echo     QuickInvoice - Auto Setup ^& Launcher
echo  ============================================
echo.

:: ── Step 1: Check for Python ──
echo  [1/5] Checking for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ERROR: Python is not installed or not in PATH.
    echo.
    echo  Please install Python 3.10+ from:
    echo  https://www.python.org/downloads/
    echo.
    echo  Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
echo         Found Python %PY_VER%

:: ── Step 2: Create virtual environment if missing ──
echo  [2/5] Checking virtual environment...
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo         Creating virtual environment...
    python -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo  ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo         Virtual environment created.
) else (
    echo         Virtual environment found.
)

:: Activate venv
call "%VENV_DIR%\Scripts\activate.bat"

:: ── Step 3: Install / update dependencies ──
echo  [3/5] Installing ^& updating dependencies...
pip install --upgrade pip >nul 2>&1
pip install --upgrade -r "%REQ_FILE%" >nul 2>&1
if %errorlevel% neq 0 (
    echo         Retrying with verbose output...
    pip install --upgrade -r "%REQ_FILE%"
    if %errorlevel% neq 0 (
        echo  ERROR: Failed to install dependencies.
        pause
        exit /b 1
    )
)
echo         All dependencies up to date.

:: ── Step 4: Rebuild .exe if source changed ──
echo  [4/5] Checking if rebuild is needed...

set "NEED_BUILD=0"

:: Check if exe exists
if not exist "%EXE_FILE%" (
    set "NEED_BUILD=1"
    echo         No .exe found - building...
)

:: Check if source is newer than exe
if exist "%EXE_FILE%" (
    for %%A in ("%APP_FILE%") do set "SRC_DATE=%%~tA"
    for %%A in ("%EXE_FILE%") do set "EXE_DATE=%%~tA"

    :: Use certutil hash to detect actual content changes
    set "CURRENT_HASH="
    for /f "skip=1 tokens=*" %%h in ('certutil -hashfile "%APP_FILE%" MD5 2^>nul') do (
        if not defined CURRENT_HASH set "CURRENT_HASH=%%h"
    )

    set "LAST_HASH="
    if exist "%HASH_FILE%" (
        set /p LAST_HASH=<"%HASH_FILE%"
    )

    if not "!CURRENT_HASH!"=="!LAST_HASH!" (
        set "NEED_BUILD=1"
        echo         Source code changed - rebuilding...
    )
)

if "!NEED_BUILD!"=="1" (
    echo         Building QuickInvoice.exe ...
    pyinstaller --noconfirm --onefile --windowed --name "QuickInvoice" --collect-all customtkinter "%APP_FILE%" >nul 2>&1
    if %errorlevel% neq 0 (
        echo         Build failed, falling back to running from source...
        goto :run_source
    )
    :: Save the hash
    set "CURRENT_HASH="
    for /f "skip=1 tokens=*" %%h in ('certutil -hashfile "%APP_FILE%" MD5 2^>nul') do (
        if not defined CURRENT_HASH set "CURRENT_HASH=%%h"
    )
    echo !CURRENT_HASH!>"%HASH_FILE%"

    :: Copy updated exe to Desktop
    copy /y "%EXE_FILE%" "%USERPROFILE%\Desktop\QuickInvoice.exe" >nul 2>&1
    echo         Build complete. Desktop copy updated.
) else (
    echo         App is up to date.
)

:: ── Step 5: Launch ──
echo  [5/5] Launching QuickInvoice...
echo.
echo  ============================================
echo     QuickInvoice is running!
echo     Close this window to stop the app.
echo  ============================================
echo.

if exist "%EXE_FILE%" (
    start "" "%EXE_FILE%"
) else (
    :run_source
    python "%APP_FILE%"
)

endlocal
