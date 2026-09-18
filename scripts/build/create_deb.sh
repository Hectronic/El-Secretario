#!/bin/bash
# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.

# Debian (.deb) Package Builder for El Secretario.

set -e

# Define directories
PKG_DIR="/tmp/el-secretario-deb"
DIST_DIR="dist"

echo "=========================================================="
echo "    El Secretario - Debian (.deb) Package Builder"
echo "=========================================================="

# Clean up previous builds
rm -rf "$PKG_DIR"
mkdir -p "$DIST_DIR"
mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/usr/bin"
mkdir -p "$PKG_DIR/usr/share/applications"
mkdir -p "$PKG_DIR/usr/share/pixmaps"

# 1. Create control file
cat << 'EOF' > "$PKG_DIR/DEBIAN/control"
Package: el-secretario
Version: 1.0.0
Architecture: all
Maintainer: Hector Alvarez <hector.alvarez@diagroup.com>
Depends: git, python3, python3-venv, ffmpeg, portaudio19-dev
Description: Intelligent audio transcription and organization tool.
 El Secretario is an intelligent tool that helps you manage recordings
 and notes with local STT (Whisper, sherpa-onnx) and RAG capabilities.
EOF

# 2. Create post-installation script
cat << 'EOF' > "$PKG_DIR/DEBIAN/postinst"
#!/bin/bash
set -e
chmod +x /usr/bin/el-secretario
echo "=========================================================="
echo "✅ El Secretario has been successfully packaged & installed!"
echo "Run 'el-secretario' in your terminal or select it from"
echo "your desktop applications menu to perform the first-run"
echo "initialization and start using the app with auto-updates!"
echo "=========================================================="
EOF
chmod 755 "$PKG_DIR/DEBIAN/postinst"

# 3. Create launcher script
cat << 'EOF' > "$PKG_DIR/usr/bin/el-secretario"
#!/usr/bin/env bash
set -e

INSTALL_DIR="$HOME/.local/share/El-Secretario"
REPO_URL="https://github.com/Hectronic/El-Secretario.git"

echo "Starting El Secretario Launcher..."

if [ ! -d "$INSTALL_DIR" ]; then
    echo "[INFO] Performing first-run setup..."
    echo "[INFO] Cloning repository to $INSTALL_DIR..."
    git clone -b main "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# Extremely robust virtual environment and dependency check
if [ ! -d ".venv" ] || [ ! -f ".venv/bin/python" ] || ! ".venv/bin/python" -c "import PyQt6" &>/dev/null; then
    echo "[INFO] Creating/fixing Python virtual environment..."
    python3 -m venv .venv
    echo "[INFO] Installing/updating dependencies (this may take a moment)..."
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
fi

# Trigger transparent auto-updates on launch using virtualenv python directly
echo "[INFO] Checking for auto-updates..."
.venv/bin/python src/auto_updater.py || echo "[WARNING] Auto-updater skipped or failed. Continuing..."

echo "[INFO] Launching El Secretario..."
.venv/bin/python main.py "$@"
EOF
chmod 755 "$PKG_DIR/usr/bin/el-secretario"

# 4. Create desktop application entry
cat << 'EOF' > "$PKG_DIR/usr/share/applications/el-secretario.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=El Secretario
Comment=Intelligent audio transcription and organization tool
Exec=/usr/bin/el-secretario
Icon=/usr/share/pixmaps/el-secretario.png
Terminal=false
StartupWMClass=el-secretario
Categories=Utility;AudioVideo;Office;
EOF

# 5. Copy logo image
if [ -f "resources/logo.png" ]; then
    cp resources/logo.png "$PKG_DIR/usr/share/pixmaps/el-secretario.png"
else
    echo "[WARNING] resources/logo.png not found, using generic icon."
fi

# 6. Build debian package
echo "Compiling Debian (.deb) package..."
dpkg-deb --build "$PKG_DIR" "$DIST_DIR/el-secretario.deb"

# Clean up
rm -rf "$PKG_DIR"

echo "=========================================================="
echo "🎉 DEBIAN PACKAGE BUILD SUCCESSFUL!"
echo "Package available at: $DIST_DIR/el-secretario.deb"
echo "You can install it with: sudo dpkg -i $DIST_DIR/el-secretario.deb"
echo "=========================================================="
