#!/usr/bin/env bash
set -e

echo "================================================"
echo "      El Secretario - Installation Script       "
echo "================================================"

# Check dependencies
command -v git >/dev/null 2>&1 || { echo >&2 "Error: git is required but it's not installed. Aborting."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo >&2 "Error: python3 is required but it's not installed. Aborting."; exit 1; }

# Define installation directory
if [ "$(uname)" == "Darwin" ]; then
    # macOS
    INSTALL_DIR="$HOME/Library/Application Support/El-Secretario"
else
    # Linux
    INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/El-Secretario"
fi

REPO_URL="https://github.com/Hectronic/El-Secretario.git"

echo "Installing El Secretario to $INSTALL_DIR..."

if [ -d "$INSTALL_DIR" ]; then
    echo "Directory already exists. Updating repository..."
    cd "$INSTALL_DIR"
    git fetch origin main
    git reset --hard origin/main
else
    echo "Cloning repository..."
    git clone -b main "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

echo "Setting up Python virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "Installing dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo "================================================"
echo "Installation complete!"
echo "You can now run El Secretario by executing:"
echo "cd \"$INSTALL_DIR\" && .venv/bin/python main.py"
echo "================================================"
