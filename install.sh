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
echo "Setting up OS Integration..."

if [ "$(uname)" == "Darwin" ]; then
    # macOS: Create an AppleScript wrapper app
    APP_PATH="$HOME/Applications/El Secretario.app"
    echo "Creating macOS application at $APP_PATH..."
    mkdir -p "$HOME/Applications"
    osacompile -o "$APP_PATH" -e "do shell script \"cd '$INSTALL_DIR' && '$INSTALL_DIR/.venv/bin/python' main.py >/dev/null 2>&1 &\""
    # Replace default icon
    if [ -f "$INSTALL_DIR/logo.icns" ]; then
        cp "$INSTALL_DIR/logo.icns" "$APP_PATH/Contents/Resources/applet.icns"
        touch "$APP_PATH" # Touch to force Finder icon refresh
    fi
else
    # Linux: Create a .desktop file
    DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
    DESKTOP_FILE="$DESKTOP_DIR/el-secretario.desktop"
    echo "Creating Linux desktop shortcut at $DESKTOP_FILE..."
    mkdir -p "$DESKTOP_DIR"
    
    cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=El Secretario
Comment=Intelligent audio transcription and organization tool
Exec="$INSTALL_DIR/.venv/bin/python" "$INSTALL_DIR/main.py"
Icon=$INSTALL_DIR/logo.png
Terminal=false
Categories=Utility;AudioVideo;
EOF
    chmod +x "$DESKTOP_FILE"
fi

echo "================================================"
echo "Installation complete!"
echo "El Secretario is now available in your applications menu."
echo "Alternatively, you can run it via terminal:"
echo "cd \"$INSTALL_DIR\" && .venv/bin/python main.py"
echo "================================================"
