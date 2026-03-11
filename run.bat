@echo off
setlocal

cd /d "%~dp0"

set "PY312=%LocalAppData%\Programs\Python\Python312\python.exe"
set "PY311=%LocalAppData%\Programs\Python\Python311\python.exe"

if not exist "venv\Scripts\python.exe" (
  echo [INFO] Virtual environment not found. Creating venv...
  if exist "%PY312%" (
    "%PY312%" -m venv venv
  ) else if exist "%PY311%" (
    "%PY311%" -m venv venv
  ) else (
    py -3.12 -m venv venv 2>nul || py -3.11 -m venv venv 2>nul || py -3 -m venv venv 2>nul || python -m venv venv
  )
  if errorlevel 1 (
    echo [ERROR] Could not create venv.
    exit /b 1
  )
)

venv\Scripts\python.exe -c "import sys; raise SystemExit(0 if (3,10) <= sys.version_info[:2] <= (3,12) else 1)" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Unsupported Python version in venv.
  venv\Scripts\python.exe --version
  echo [ERROR] This project currently supports Python 3.10 to 3.12 for pinned ML dependencies.
  echo [ERROR] Recreate venv with Python 3.12 or run reinstall_and_run.bat after installing Python 3.12.
  exit /b 1
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
