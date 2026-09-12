# SPEC-023: Transparent Auto-Updater

Status: Draft
Owner: TBD
Last updated: 2026-09-12

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

- The updating logic should ideally reside in the OS-level launcher script (e.g., a `.bat` or `.sh` wrapper) that runs before the Python environment is fully loaded. This prevents issues with updating files that are currently in use by the Python process (especially on Windows).
- Flow:
  1. `git fetch origin main`
  2. Check if local `main` is behind `origin/main`.
  3. If behind: `git pull origin main`.
  4. If `requirements.txt` changed in the diff: update virtual environment.
  5. Launch the actual application (`python main.py`).
- Hide console output during this process unless an unrecoverable error occurs.

## Test Plan

- Unit: Test the update check logic in isolation (mocking git commands).
- Integration: Simulate a new commit on the remote branch, launch the app, and verify that the local repo is updated and the app starts successfully.
- Manual: Test offline behavior to ensure the app doesn't hang. Test with a modified `requirements.txt` to ensure dependencies are installed.

## Documentation

- Add a section in `README.md` explaining the auto-update behavior and how developers can disable it if they are working on local changes.
