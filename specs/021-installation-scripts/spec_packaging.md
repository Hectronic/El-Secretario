# SPEC-021: Native Packaging and Auto-Updating Installers

Status: Implemented
Owner: Héctor Álvarez López <hector.alvarez@diagroup.com>
Last updated: 2026-09-15

## Problem

While we have automated installation shell/batch scripts (`install.sh` and `install.bat`), end-users expect standard native OS installation files:
- A Debian/Ubuntu `.deb` package.
- A Windows `.exe` installer.
- A macOS `.pkg` or `.dmg` installer.

These installers must install the application in a way that respects standard system locations and permissions, yet preserves full git-based self-updating capabilities (from the `main` branch), so that the application can transparently update itself without requiring administrative privileges, with a toggleable setting in the UI.

## Scope

- **In scope:**
  - Creating native packaging definitions and build scripts for:
    - Ubuntu/Debian: `.deb` package using `dpkg-deb`.
    - Windows: `.exe` installer using Inno Setup or NSIS.
    - macOS: `.dmg` or `.pkg` package using `pkgbuild` and Apple script bundling.
  - A standardized "Bootstrapper & Launcher" strategy that:
    - Automatically checks/clones the repository to a writable user-space folder (`~/.local/share/El-Secretario`, `%LocalAppData%\El-Secretario`, or `~/Library/Application Support/El-Secretario`).
    - Handles setting up the python virtual environment.
    - Runs the early startup `auto_updater.py` logic to apply updates.
  - Proper integration of the "Enable Auto-Updates" setting toggle in Settings.
- **Out of scope:**
  - Fully compiled binary packages (e.g., using PyInstaller for the entire runtime) that don't allow git self-updating. The distribution model remains source-cloned via Git to enable instant, friction-free updates.

## Architecture & Packaging Strategy

### 1. Ubuntu/Debian `.deb` Package
- **Package name:** `el-secretario`
- **Installation Path:** `/opt/el-secretario` (system files) and user-specific cloning in `~/.local/share/El-Secretario`.
- **Packaging Method:**
  - Build directory structure:
    ```
    el-secretario-pkg/
    ├── DEBIAN/
    │   ├── control       # Metadata, architecture, dependencies (git, python3, python3-venv, ffmpeg, portaudio19-dev)
    │   └── postinst      # Script running after installation to set up permissions and prepare launcher
    ├── usr/
    │   ├── bin/
    │   │   └── el-secretario                  # Global symlink launcher script
    │   └── share/
    │       ├── applications/
    │       │   └── el-secretario.desktop      # Desktop application entry
    │       └── pixmaps/
    │           └── el-secretario.png          # App icon
    ```
  - **Launch Logic:**
    - `/usr/bin/el-secretario` is a bash wrapper script.
    - When executed, it checks if `~/.local/share/El-Secretario` contains a valid git clone of the repository.
    - If not, it clones the repo to `~/.local/share/El-Secretario` and initializes the `.venv`.
    - If yes, it activates the virtual environment, executes `python src/auto_updater.py`, and launches `python main.py`.
    - This bypasses root write restrictions under `/opt/` or `/usr/`, ensuring the auto-updater can safely run `git pull` and `pip install` entirely in user-space!

### 2. Windows `.exe` Installer
- **Packaging Tool:** **Inno Setup** (free, highly scriptable compiler for Windows installers).
- **Setup script (`setup.iss`):**
  - Defines installer metadata, icons, and shortcuts.
  - Installs the app bootstrapper directly into `{localappdata}\El-Secretario`. Since `{localappdata}` is fully writable by the current user without administrative privileges, git can safely update files.
  - **Dependencies:** The installer checks if `git` and `python` (supported version 3.10-3.12) are installed. If missing, it prompts the user with direct download links.
  - **Post-Install Action:** Runs `install.bat` in the background to initialize the repository clone, virtual environment, and dependency installation.
  - Creates a Desktop and Start Menu shortcut pointing to `run.bat` (which calls `src/auto_updater.py` followed by `main.py`).

### 3. macOS `.dmg` or `.pkg` Bundle
- **Packaging Tool:** `pkgbuild` or `create-dmg` wrapper.
- **macOS Bundle (`El Secretario.app`):**
  - Compiled as a macOS `.app` shell bundle that is installed to `/Applications/El Secretario.app`.
  - **Contents/MacOS/El Secretario Launcher:**
    - A bash wrapper script inside the bundle.
    - Checks if `~/Library/Application Support/El-Secretario` contains the repository clone. If missing, it clones it there and sets up the `.venv`.
    - Automatically checks for standard macOS dependencies (Homebrew git, python, ffmpeg) and assists the user.
    - Executes the virtual environment python with the `auto_updater.py` script, then runs `main.py`.
    - This adheres perfectly to macOS security guidelines (as `/Applications` is read-only for regular users, but `~/Library/Application Support` has full user-space write access for seamless auto-updates).

## Root Folder Cleanup & Organization

To maintain a clean, enterprise-grade codebase, the root folder of the repository should be streamlined. Cluttered scripts, assets, build configurations, and debug helpers will be reorganized as follows:

### 1. Retention in Root Directory
Only critical project files and entry points remain in the root folder:
- `main.py` (Core entry point)
- `requirements.txt` (Dependencies pin)
- `run.sh` / `run.bat` (Quick-run developer wrappers)
- Essential documentation: `README.md`, `README_ES.md`, `README_AST.md`, `CONTRIBUTING.md`, `LICENSE`, `PROJECT_EVOLUTION.md`, `AGENTS.md`, `GEMINI.md`.

### 2. Assets Folder (`resources/`)
Move the following visual assets from the root to `resources/`:
- `logo.png`, `logo.ico`, `logo.icns`
- Update any direct paths inside the source code (e.g., in `main.py`, `MainWindow` icon configuration, macOS bundle configs, and `.desktop` templates) to use the new `resources/` path relative to the application base.

### 3. Build & Packaging Folder (`scripts/build/`)
Move build-related and native installer compiling files to `scripts/build/`:
- `build_ubuntu.sh`
- `build_windows.bat`
- `ElSecretario.spec` (PyInstaller specification)
- Standard OS install scripts: `install.sh`, `install.bat` (Moved to `scripts/install/` with root-level redirection or clear documentation).

### 4. Development & Pipeline Scripts (`scripts/`)
Move general development wrappers and pipeline validation scripts to `scripts/`:
- `reinstall_and_run.sh` / `reinstall_and_run.bat`
- `run_with_test.sh`
- `verify_pipeline.sh`

### 5. Debug Helpers (`debug/`)
Move isolated troubleshooting and debugging scripts to `debug/`:
- `debug_flow.py`
- `debug_mainwindow.py`
- `debug_tasks_widget.py`
- `debug_tests.sh`

## Acceptance Criteria

- **Debian Package:**
  - Running `sudo dpkg -i el-secretario.deb` installs the desktop shortcut and launcher cleanly.
  - Launching the app via applications menu clones the repo to user-space, creates the venv, updates it, and boots the application.
  - The application updates itself automatically on subsequent launches if changes are found on `origin/main`.
- **Windows Installer:**
  - Double-clicking the `.exe` installer installs files directly into `{localappdata}\El-Secretario` without asking for Admin (UAC) elevation.
  - Creating/running the application launches the auto-update check seamlessly.
- **macOS Installer:**
  - Opening the `.dmg` allows dragging `El Secretario.app` to `/Applications`.
  - Launching the app executes successfully, cloning the writable code base to `~/Library/Application Support/El-Secretario` and starting.
- **UI Setting Integration:**
  - The **🔄 Auto-Updater** toggle checkbox in the General Settings panel enables or disables this startup behavior.
  - When disabled, `auto_updater.py` immediately exits on startup, allowing developers to work on local changes without them being overwritten.

## Test and Validation Plan

- **Simulated Installation Tests:**
  - Run the package build pipelines on target operating systems.
  - Verify that installing the packages and launching the app on fresh systems clones, updates, and runs El Secretario cleanly.
- **Auto-Update Toggling Verification:**
  - Toggle off "Enable automatic updates" in Settings. Verify that launching the app doesn't trigger git fetch or pull.
  - Toggle on "Enable automatic updates". Verify that launching the app triggers the check.
