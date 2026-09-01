# REFACTOR-2026-09-RECORD-ACTIONS: Recording Detail Actions

Status: Implemented
Last updated: 2026-09-01

## Goal

Move user-triggered recording-detail actions and playback adapters out of the broad recording widget.

## Behavior Contract

- Preserved: confirmed deletion removes the database record, local audio when present, and RAG document when available, then emits the existing deletion signal.
- Preserved: opening the audio editor and chat emits the existing public widget signals and recording context shape.
- Preserved: playback controls, media-end stop behavior, slider synchronization, and action enablement remain unchanged.
- Changed: none.

## Moved Boundary

- From: `src/ui/recording_widget.py`.
- To: `src/ui/recording/record_actions.py` (`RecordingActionsCoordinator`).
- Compatibility: `RecordingWidget` retains its existing public slots as delegates for Qt signal connections and callers.

## Specs Affected

- SPEC-004: Recording Metadata, Notes, Favorites, And Deletion.
- SPEC-005: Waveform Audio Editor And Safe Retranscription.
- SPEC-007: Chat Sessions, Context Builder, And Floating Chat.

## Tests

- Focused: `tests/ui/recording/test_record_actions.py`, `tests/test_recording_widget_ui.py`, `tests/test_recording_flow.py`, `tests/test_deletion.py`, and `tests/ui/main_window/test_recording_tabs.py`.
- Full suite: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./venv/bin/python -m pytest -q`.

## Follow-Ups

- Extract record loading/saving and its persistence/RAG orchestration without changing the widget's dirty-state contract.
