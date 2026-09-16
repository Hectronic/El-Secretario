#!/bin/bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"

if [ ! -x "./venv/bin/python" ]; then
  echo "Missing ./venv. Create it first:"
  echo "  python3 -m venv venv"
  echo "  ./venv/bin/pip install -r requirements.txt"
  exit 1
fi

./venv/bin/python -m pytest -q "$@"
