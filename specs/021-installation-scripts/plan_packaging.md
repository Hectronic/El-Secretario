# Implementation Plan: Native Packaging and Auto-Updating Installers

Status: Draft
Last updated: 2026-09-15
Spec: [spec_packaging.md](spec_packaging.md)

## Phases

### Phase 1: Debian/Ubuntu Packaging
- Define the `DEBIAN/control` file with dependencies.
- Write the `postinst` and `prerm` scripts to configure symlinks and groups.
- Write `/usr/bin/el-secretario` launcher wrapper with cloning & auto-update logic.
- Create system applications shortcut `el-secretario.desktop` and add application icon.
- Test building with `dpkg-deb --build` and install on a clean Ubuntu image.

### Phase 2: Windows Installer Packaging
- Install Inno Setup on Windows build system.
- Write `installer.iss` script with metadata, icons, and local-appdata installation target.
- Implement prerequisite check for Git for Windows and Python (supported versions 3.10-3.12).
- Configure post-installation execution of `install.bat`.
- Test running the compiled `.exe` installer.

### Phase 3: macOS Bundle and DMG creation
- Write the macOS shell script launcher `Contents/MacOS/El Secretario` inside the `.app` bundle.
- Configure `Contents/Info.plist` with app categories, icons, and bundle details.
- Write code to clone to `~/Library/Application Support/El-Secretario` and run the update checks.
- Build `.dmg` package using `create-dmg` tool.
- Test dragging the app to `/Applications` on macOS.

### Phase 4: Full Validation & Testing
- Validate the auto-update checkbox toggling from settings under each platform's native installation.
- Verify that developers can safely override updates using `DISABLE_AUTO_UPDATE=1`.

### Phase 5: Root Folder Reorganization & Cleanup
- Create folders `resources/`, `debug/`, `scripts/build/`, and `scripts/install/`.
- Move visual assets (`logo.png`, `logo.ico`, `logo.icns`) to `resources/` and update references inside code.
- Move troubleshooting scripts to `debug/`.
- Move build configurations to `scripts/build/`.
- Move install helpers to `scripts/install/` and other runner wrappers to `scripts/`.
- Ensure `run.sh` / `run.bat` remain in the root directory as clean, zero-friction developer launchers.
