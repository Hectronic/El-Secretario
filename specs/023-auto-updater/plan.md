# Implementation Plan: Auto Updater

Status: Completed
Last updated: 2026-09-15
Spec: [spec.md](spec.md)

## Architecture & Design

We designed a unified, cross-platform Auto-Updater system for El Secretario with three main tiers:

1. **Early-stage Auto-Updater Module (`src/auto_updater.py`):**
   - Implements lightweight, robust checks on launch to see if the current branch (`main`) is behind `origin/main`.
   - Utilizes `git fetch` with a strict 3-second connection timeout, ensuring offline situations are handled gracefully and silently.
   - If updates are available, it automatically pulls updates cleanly.
   - If `requirements.txt` was modified in the incoming commits, it automatically executes the equivalent of `pip install -r requirements.txt` within the current active virtual environment (`sys.executable`).

2. **Early-Stage Integration in `main.py`:**
   - On startup (before initializing PyQt application loops or any UI components), `main.py` runs the auto-updater check.
   - If updates are successfully applied, the script automatically restarts itself cleanly using `os.execv` to load the freshly updated code. This completely avoids "half-loaded" files and Windows file locking issues.

3. **Periodic & Interactive UI Integration:**
   - Implemented a background QThread `UpdateCheckerThread` inside `src/ui/main_window/update_checker.py` to prevent blocking the UI thread.
   - Integrated setting control checkbox (`enable_auto_update`) and interactive "Check for Updates" button within the `GeneralSettingsPanel` (`src/ui/settings/general_panel.py`).
   - If updates are detected interactively, the app prompts the user if they'd like to update and restart immediately, executing a safe resource teardown first.

## Validation Results

We wrote and executed a comprehensive test suite in `tests/test_auto_updater.py` covering:
- Default status, environment overrides (`DISABLE_AUTO_UPDATE`), and QSettings control.
- Git repository checks, branch isolation (updating only from branch `main`), and network timeout/offline fallbacks.
- Git pull execution, pip requirements update triggers, and signal/callback emission inside `UpdateCheckerThread`.

All unit, integration, and UI settings tests pass successfully:
- `tests/test_auto_updater.py`: 13 Passed.
- `tests/test_settings.py`: 7 Passed.
Total: 20 passed.
