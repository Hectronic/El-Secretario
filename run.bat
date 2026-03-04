@echo off
setlocal

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
  echo [INFO] Virtual environment not found. Creating venv...
  py -3 -m venv venv 2>nul || python -m venv venv
  if errorlevel 1 (
    echo [ERROR] Could not create venv.
    exit /b 1
  )
)

echo [INFO] Installing/updating dependencies...
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
