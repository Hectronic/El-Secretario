#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

echo "[INFO] Removing existing virtual environments..."
rm -rf venv .venv

echo "[INFO] Creating fresh virtual environment..."
if command -v python3 >/dev/null 2>&1; then
  python3 -m venv venv
else
  python -m venv venv
fi

echo "[INFO] Upgrading pip..."
./venv/bin/python -m pip install --upgrade pip

echo "[INFO] Installing requirements..."
./venv/bin/python -m pip install -r requirements.txt

echo "[INFO] Starting El Secretario..."
./venv/bin/python main.py
