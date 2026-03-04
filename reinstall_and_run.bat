@echo off
setlocal

cd /d "%~dp0"

echo [INFO] Removing existing virtual environments...
if exist "venv" rmdir /s /q "venv"
if exist ".venv" rmdir /s /q ".venv"

echo [INFO] Creating fresh virtual environment...
py -3 -m venv venv 2>nul || python -m venv venv
if errorlevel 1 (
  echo [ERROR] Could not create venv.
  exit /b 1
)

echo [INFO] Upgrading pip...
venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 (
  echo [ERROR] pip upgrade failed.
  exit /b 1
)

echo [INFO] Installing requirements...
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] Dependency installation failed.
  exit /b 1
)

echo [INFO] Starting El Secretario...
venv\Scripts\python.exe main.py
if errorlevel 1 (
  echo [ERROR] Application exited with error.
  exit /b 1
)

endlocal
