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

# macOS Application Bundle & DMG Builder for El Secretario

set -e

APP_NAME="El Secretario"
DIST_DIR="dist"
APP_BUNDLE="$DIST_DIR/$APP_NAME.app"

echo "=========================================================="
echo "    El Secretario - macOS App Bundle & DMG Builder"
echo "=========================================================="

# Clean up previous builds
rm -rf "$APP_BUNDLE" "$DIST_DIR/$APP_NAME.dmg"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

# 1. Create Info.plist
cat << 'EOF' > "$APP_BUNDLE/Contents/Info.plist"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>El Secretario</string>
    <key>CFBundleDisplayName</key>
    <string>El Secretario</string>
    <key>CFBundleIdentifier</key>
    <string>com.hectronic.elsecretario</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleExecutable</key>
    <string>El Secretario</string>
    <key>CFBundleIconFile</key>
    <string>applet.icns</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# 2. Create the launcher bootstrapper
cat << 'EOF' > "$APP_BUNDLE/Contents/MacOS/El Secretario"
#!/usr/bin/env bash
# macOS User-Space Bootstrapper launcher for El Secretario
set -e

INSTALL_DIR="$HOME/Library/Application Support/El-Secretario"
REPO_URL="https://github.com/Hectronic/El-Secretario.git"

echo "Starting El Secretario macOS Launcher..."

if [ ! -d "$INSTALL_DIR" ]; then
    echo "[INFO] Performing first-run setup..."
    echo "[INFO] Cloning repository to $INSTALL_DIR..."
    git clone -b main "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# Check and fix virtual environment
if [ ! -d ".venv" ] || [ ! -f ".venv/bin/python" ] || ! ".venv/bin/python" -c "import PyQt6" &>/dev/null; then
    echo "[INFO] Creating/fixing Python virtual environment..."
    python3 -m venv .venv
    echo "[INFO] Installing/updating dependencies (this may take a moment)..."
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
fi

# Run auto-updates using the virtual environment python directly
echo "[INFO] Checking for auto-updates..."
.venv/bin/python src/auto_updater.py || echo "[WARNING] Auto-updater skipped or failed. Continuing..."

echo "[INFO] Launching El Secretario..."
.venv/bin/python main.py "$@"
EOF
chmod +x "$APP_BUNDLE/Contents/MacOS/El Secretario"

# 3. Copy visual icon asset
if [ -f "resources/logo.icns" ]; then
    cp resources/logo.icns "$APP_BUNDLE/Contents/Resources/applet.icns"
else
    echo "[WARNING] resources/logo.icns not found, using generic icon placeholder."
fi

echo "=========================================================="
echo "✅ macOS App Bundle constructed successfully at: $APP_BUNDLE"
echo "=========================================================="

# 4. Compile to DMG (Requires macOS hdiutil)
if [ "$(uname)" == "Darwin" ]; then
    echo "Compiling .dmg disk image..."
    # Build standard DMG using macOS command line tool
    hdiutil create -volname "$APP_NAME Installation" -srcfolder "$APP_BUNDLE" -ov -format UDZO "$DIST_DIR/$APP_NAME.dmg"
    echo "=========================================================="
    echo "🎉 macOS .dmg Disk Image compiled successfully!"
    echo "DMG file available at: $DIST_DIR/$APP_NAME.dmg"
    echo "=========================================================="
else
    echo "[INFO] Build platform is not macOS. Skipping .dmg compilation."
    echo "[INFO] You can compile this into a DMG on a Mac by running:"
    echo "       hdiutil create -volname \"$APP_NAME\" -srcfolder \"$APP_BUNDLE\" -ov -format UDZO \"$DIST_DIR/$APP_NAME.dmg\""
    echo "=========================================================="
fi
