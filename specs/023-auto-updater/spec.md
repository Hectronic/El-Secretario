# SPEC-023: Transparent Auto-Updater

Status: Implemented
Owner: Héctor Álvarez López <hector.alvarez@diagroup.com>
Last updated: 2026-09-15

## Problem

Because the application is distributed as a source clone, updates require the user to manually pull from `main` and potentially reinstall requirements. To ensure users always have the latest features and bug fixes without friction, the application should transparently check for updates and apply them upon launch.

## Scope

- In scope: 
  - A startup launcher script or an early Python routine that checks the remote `origin/main` for updates.
  - Transparently executing `git pull` if an update is found.
  - Automatically synchronizing dependencies if `requirements.txt` has changed.
  - Handling update failures gracefully (falling back to the current version).
- Out of scope: Complex rollback mechanisms (beyond simple git resets if an update immediately fails), differential binary patching.

## User Stories

- As a user, I want the application to automatically update itself when I launch it so I don't have to remember to check for new versions.
- As a user, I want the update process to be completely transparent and fast, only delaying the startup slightly when an update is actually downloaded.

## Acceptance Criteria

- Given the application is launched, when there are no new commits on `origin/main`, then the application starts normally without noticeable delay.
- Given there are new commits on `origin/main`, when the application is launched, then it automatically fetches and pulls the changes before starting the main UI.
- Given a pull includes dependency changes, then the updater automatically runs the equivalent of `pip install -r requirements.txt`.
- Given the user has no internet connection, when the application is launched, then the update check silently times out and the app launches the local version.

## Architecture Notes

The transparent auto-updater is implemented across three coordinated architectural layers:

### 1. Early Startup Module (`src/auto_updater.py`)
- Executes before the GUI loaded or any PyQt window is created.
- Runs `git fetch origin main` with a strict 3-second connection timeout, handling offline scenarios silently.
- Compares commit hashes (`git merge-base --is-ancestor`) to see if the local branch `main` is behind `origin/main`.
- If behind, executes a clean `git pull`. If `requirements.txt` was modified, runs the virtualenv's pip executable directly (`.venv/bin/pip` or equivalent via `sys.executable`) to update packages.

### 2. Process Replacement in `main.py`
- On startup, if an update was successfully applied, the app immediately reloads itself by calling `os.execv(sys.executable, [sys.executable] + sys.argv)`. This prevents files in use or "half-loaded" modules, solving Windows locks.

### 3. Background Threads & Settings Integration
- Added an `UpdateCheckerThread` (`QThread`) running in the background while the UI is open.
- Integrated an "Enable automatic updates" checkbox in the Settings General Panel, saving `enable_auto_update` in QSettings.
- Added a "Check for Updates" button to let users trigger updates in real-time and prompt for immediate restart.

## Test Plan

- Unit: Test the update check logic in isolation (mocking git commands).
- Integration: Simulate a new commit on the remote branch, launch the app, and verify that the local repo is updated and the app starts successfully.
- Manual: Test offline behavior to ensure the app doesn't hang. Test with a modified `requirements.txt` to ensure dependencies are installed.

## Documentation

- Add a section in `README.md` explaining the auto-update behavior and how developers can disable it if they are working on local changes.
