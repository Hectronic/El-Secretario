# SPEC-001: Audio Capture And Import

Status: Implemented
Owner: TBD
Last updated: 2026-06-27

## Problem

Users need a fast landing surface to start a recording, import audio, search, and jump into the day-to-day navigation paths of the app. The welcome screen also persists the recording configuration that powers capture and import flows.

## Scope

- In scope: welcome screen layout, recording/import entry points, microphone selection, capture settings persistence, mic test controls, quick search, favorites, today view, and launch shortcuts for notes, chat, tools, and settings.
- Out of scope: transcription internals, recording editing, chat session state, search result rendering, and database schema redesign.

## User Stories

- As a user, I want to start a recording from the landing screen so that capture is immediate.
- As a user, I want to import audio with the same capture settings so that imported recordings behave consistently.
- As a user, I want to pick the microphone and related capture options once so that the app remembers my preferences.
- As a user, I want to test the microphone from the landing screen so that I can verify input before recording.
- As a user, I want to reach search, favorites, today content, notes, chat, tools, and settings from one place so that the app stays quick to navigate.

## Acceptance Criteria

- Given the welcome screen is opened, when it initializes, then it restores saved microphone, model, language, diarization, system-audio, and auto-summary settings.
- Given the user changes a capture option, when the control changes, then the new configuration is persisted to `QSettings`.
- Given the user clicks the record or import actions, when capture is about to start, then the current recording configuration is emitted with the action signal.
- Given the user starts the microphone test, when the test is running, then the UI shows live level feedback and the test can be stopped cleanly.
- Given the user clicks search, when text is present, then the welcome screen emits the search request with the entered query.
- Given the user clicks shortcuts for notes, chat, tools, settings, favorites, or today, when the action is available, then the corresponding navigation or signal is triggered.

## Architecture Notes

- UI: `src/ui/welcome_widget.py` owns the landing widget composition and user-facing signals.
- UI helpers: `src/ui/welcome/button_factory.py` owns the reusable button constructors used by the welcome screen.
- Capture helpers: `src/ui/welcome/capture_state.py` owns capture-setting persistence, microphone list hydration, and recording config mapping.
- Mic test helpers: `src/ui/welcome/mic_test.py` owns stream startup/cleanup, RMS calculation, and VU meter state updates.
- Landing data helpers: `src/ui/welcome/landing_data.py` owns search-result, favorites, and today-list query formatting for the welcome screen.
- Main window: `src/ui/main_window/` wires welcome-screen signals into tabs, sidebar state, and daily-summary actions.
- Persistence: `QSettings` stores capture preferences and the welcome widget reads them back on startup.
- Workers/integrations: recorder startup, import flow, and search all route into downstream capture/search services rather than implementing heavy logic inside the widget.
- Platform constraints: preserve Ubuntu and Windows behavior, including resource-path lookup and mic/test handling.

## Test Plan

- Unit: button constructors, signal wiring, and persisted capture-setting round trips.
- Integration: welcome-screen actions emit the correct signals and the main window receives them.
- UI: verify layout density, clock/header balance, and launch buttons.
- Manual: exercise recording, import, mic test, favorites, today, and search from the landing screen on Ubuntu and Windows.

## Documentation

- Feature registry: `docs/specs/README.md`.
- Refactor record: `docs/specs/REFACTOR-2026-05-feature-packages.md`.

## Refactor Notes

- 2026-06-10: created a dedicated spec for the welcome screen and its capture/import responsibilities.
- 2026-06-10: extracted the welcome screen button constructors into `src/ui/welcome/button_factory.py` and kept `WelcomeWidget` as the signal/layout owner.
- 2026-06-10: extracted capture-setting state helpers into `src/ui/welcome/capture_state.py`.
- 2026-06-10: extracted microphone-test lifecycle helpers into `src/ui/welcome/mic_test.py`.
- 2026-06-27: extracted welcome search-result, favorites, and today-list data formatting into `src/ui/welcome/landing_data.py`.

## Open Questions

- Should microphone scanning move from the widget wrapper into a fuller device-discovery helper once audio-device behavior has broader tests?
- Should the remaining welcome layout construction be split into focused panel builders once UI layout coverage is broader?
