@echo off
setlocal enabledelayedexpansion

echo ================================================
echo       El Secretario - Installation Script       
echo ================================================

:: Check dependencies
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo ================================================
    echo Error: git is required but it's not installed.
    echo Please install Git for Windows and try again.
    echo ================================================
    pause
    exit /b 1
)

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ================================================
    echo Error: python is required but it's not installed.
    echo Please install Python (and add to PATH) and try again.
    echo ================================================
    pause
    exit /b 1
)

:: Define installation directory
set "INSTALL_DIR=%LOCALAPPDATA%\El-Secretario"
set "REPO_URL=https://github.com/Hectronic/El-Secretario.git"

echo Installing El Secretario to %INSTALL_DIR%...

if exist "%INSTALL_DIR%" (
    echo Directory already exists. Updating repository...
    cd /d "%INSTALL_DIR%" || goto :Error
    git stash
    git pull origin main || goto :ErrorUpdate
    git stash pop || echo Done
) else (
    echo Cloning repository...
    git clone -b main "%REPO_URL%" "%INSTALL_DIR%" || goto :ErrorClone
    cd /d "%INSTALL_DIR%" || goto :Error
)

echo Setting up Python virtual environment...
if not exist ".venv" (
    python -m venv .venv || goto :ErrorVenv
)

echo Installing dependencies...
call .venv\Scripts\activate.bat || goto :ErrorVenv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt || goto :ErrorPip

goto :ContinueSetup

:Error
echo ================================================
echo Error: Failed to change directory.
echo Please fix the issue and try again.
echo ================================================
pause
exit /b 1

:ErrorUpdate
echo ================================================
echo Error: Failed to pull updates from GitHub.
echo Check your internet connection.
echo ================================================
pause
exit /b 1

:ErrorClone
echo ================================================
echo Error: Failed to clone repository from GitHub.
echo Check your internet connection.
echo ================================================
pause
exit /b 1

:ErrorVenv
echo ================================================
echo Error: Failed to create or activate Python virtual environment.
echo ================================================
pause
exit /b 1

:ErrorPip
echo ================================================
echo Error: Failed to install Python dependencies.
echo Check your internet connection or requirements.txt.
echo ================================================
pause
exit /b 1

:ContinueSetup
echo ================================================
echo Setting up OS Integration...

set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\El Secretario.lnk"
set "TARGET_PATH=%INSTALL_DIR%\.venv\Scripts\pythonw.exe"
set "WORKING_DIR=%INSTALL_DIR%"
set "SCRIPT_ARGS=""%INSTALL_DIR%\main.py"""
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
