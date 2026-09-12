@echo off
setlocal enabledelayedexpansion

echo ================================================
echo       El Secretario - Installation Script       
echo ================================================

:: Check dependencies
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: git is required but it's not installed. Aborting.
    exit /b 1
)

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: python is required but it's not installed. Aborting.
    exit /b 1
)

:: Define installation directory
set "INSTALL_DIR=%LOCALAPPDATA%\El-Secretario"
set "REPO_URL=https://github.com/Hectronic/El-Secretario.git"

echo Installing El Secretario to %INSTALL_DIR%...

if exist "%INSTALL_DIR%" (
    echo Directory already exists. Updating repository...
    cd /d "%INSTALL_DIR%"
    git fetch origin main
    git reset --hard origin/main
) else (
    echo Cloning repository...
    git clone -b main "%REPO_URL%" "%INSTALL_DIR%"
    cd /d "%INSTALL_DIR%"
)

echo Setting up Python virtual environment...
if not exist ".venv" (
    python -m venv .venv
)

echo Installing dependencies...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo ================================================
echo Installation complete!
echo You can now run El Secretario by executing:
echo cd /d "%INSTALL_DIR%" ^&^& .venv\Scripts\python.exe main.py
echo ================================================
pause
