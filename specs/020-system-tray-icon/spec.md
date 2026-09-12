# SPEC-020: System Tray Icon

Status: Draft
Owner: TBD
Last updated: 2026-09-12

## Problem

Currently, the application may only appear in the system tray under certain conditions (e.g., when recording). Users need the application to always be accessible from the system tray so they can quickly interact with it at any time. Furthermore, to provide clear visual feedback without opening the main window, the tray icon should display a small red circle indicator superimposed on its bottom corner while a recording is in progress.

## Scope

- In scope: System tray icon initialization, always-on visibility, tray context menu (show/hide app, exit), and dynamic icon updates during recording (adding a red badge).
- Out of scope: Changes to the recording engine, transcription, or main window layouts.

## User Stories

- As a user, I want the application to always display an icon in the system tray so I can easily find and open it.
- As a user, I want the tray icon to visually indicate when a recording is active (via a red circle badge) so I know when my microphone is being captured without needing to check the main app window.

## Acceptance Criteria

- Given the application is running, when the user looks at the system tray, then the application's icon is always visible.
- Given the application is in the system tray, when the user starts a recording, then a small red circle is superimposed on the bottom corner of the tray icon.
- Given the application is recording, when the recording stops or is canceled, then the tray icon returns to its default state (without the red circle).

## Architecture Notes

- UI: Create a dedicated helper/class for managing the system tray icon (e.g., `src/ui/system_tray_manager.py`) to keep the main window cleaner.
- The manager should listen to recording state signals (e.g., `recording_started`, `recording_stopped`) to update the icon dynamically.
- The red badge can be drawn using Qt's `QPainter` over the base icon, or using a secondary pre-rendered icon asset.

## Test Plan

- Unit: Test the tray manager's state updates when recording signals are received. Test that the icon rendering logic applies the badge correctly.
- Integration: Test that the main window correctly initializes the tray icon and forwards recording state signals to it.
- UI/Manual: Verify the tray icon is visible on startup, shows the recording badge when a recording starts, and removes it when stopped. Check cross-platform behavior (Windows, Ubuntu, macOS).

## Documentation

- Feature registry: `specs/README.md`.

## Refactor Notes

- N/A

## Open Questions

- Should the tray icon have a left-click default action (e.g., toggle window visibility)?
- Do we need to handle special cases for macOS where the menu bar is used instead of a traditional system tray?
