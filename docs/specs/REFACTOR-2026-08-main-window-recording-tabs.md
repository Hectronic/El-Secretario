# REFACTOR-2026-08-RECORDING-TABS: Main-Window Recording Tabs

Status: Implemented
Last updated: 2026-08-30

## Goal

Complete the recording-tab boundary by moving capture completion and tab refresh orchestration into the existing recording coordinator.

## Behavior Contract

- Preserved: single in-progress capture tab, recorder device/system-audio settings, completed-capture persistence, tags, quick tasks, transcription handoff, recording/audio-editor tab opening, title synchronization, and sidebar refreshes after save or deletion.
- Changed: none.
- Out of scope: recording-widget internals, transcription runtime, playback, and deletion persistence.

## Moved Boundaries

- From: `src/ui/main_window/__init__.py` recording start, capture completion, and recording tab save/delete callbacks.
- To: `src/ui/main_window/recording_tabs.py` (`RecordingTabCoordinator`).
- Compatibility: `MainWindow` retains the prior delegates for welcome and recording-widget signals.

## Specs Affected

- SPEC-001: Audio Capture And Import.
- SPEC-004: Recording Metadata, Notes, Favorites, And Deletion.

## Tests

- Focused: `tests/ui/main_window/test_recording_tabs.py`, `tests/test_recording_flow.py`, `tests/test_recording_widget_ui.py`, `tests/ui/recording/test_transcription_flow.py`, `tests/ui/main_window/test_setup_actions.py`, and `tests/ui/main_window/test_tab_lifecycle.py`.
- Full suite: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./venv/bin/python -m pytest -q`.

## Follow-Ups

- Extract remaining recording deletion, playback, and persistence-facing orchestration from `MainWindow` and `RecordingWidget` in separate behavior-focused cuts.
