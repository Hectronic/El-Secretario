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
echo Setting up OS Integration...

set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\El Secretario.lnk"
set "TARGET_PATH=%INSTALL_DIR%\.venv\Scripts\pythonw.exe"
set "WORKING_DIR=%INSTALL_DIR%"
set "SCRIPT_ARGS=%INSTALL_DIR%\main.py"
set "ICON_PATH=%INSTALL_DIR%\logo.ico"

echo Creating Start Menu shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$wshell = New-Object -ComObject WScript.Shell; $shortcut = $wshell.CreateShortcut('%SHORTCUT_PATH%'); $shortcut.TargetPath = '%TARGET_PATH%'; $shortcut.Arguments = '%SCRIPT_ARGS%'; $shortcut.WorkingDirectory = '%WORKING_DIR%'; $shortcut.IconLocation = '%ICON_PATH%'; $shortcut.Save()"

echo ================================================
echo Installation complete!
echo El Secretario is now available in your Start Menu.
echo Alternatively, you can run it via terminal:
echo cd /d "%INSTALL_DIR%" ^&^& .venv\Scripts\pythonw.exe main.py
echo ================================================
pause
