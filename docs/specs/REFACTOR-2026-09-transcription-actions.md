# REFACTOR-2026-09-TRANSCRIPTION-ACTIONS: Recording Direct Transcription

Status: Implemented
Last updated: 2026-09-01

## Goal

Move widget-level direct-transcription orchestration out of the recording detail widget.

## Behavior Contract

- Preserved: transcription configuration applies model, language, diarization, and auto-summary settings.
- Preserved: worker start, preflight failures, progress, status/error traces, persistence, detail reload, signals, automatic summary enqueueing, and RAG indexing keep their prior behavior.
- Preserved: the public widget slots and dependency patch points for settings, worker class, audio probing, and dialogs remain available.
- Changed: none.

## Moved Boundary

- From: `src/ui/recording_widget.py`.
- To: `src/ui/recording/transcription_actions.py` (`RecordingTranscriptionCoordinator`).
- Compatibility: `RecordingWidget` retains public slots and injects its current runtime dependencies into the coordinator.

## Specs Affected

- SPEC-002: Transcription Runtime And STT Provider Selection.
- SPEC-004: Recording Metadata, Notes, Favorites, And Deletion.
- SPEC-006: RAG Indexing And Semantic Search.
- SPEC-011: Summaries And Background Queue.

## Tests

- Focused: `tests/ui/recording/test_transcription_actions.py`, `tests/ui/recording/test_transcription_flow.py`, `tests/test_recording_widget_ui.py`, and `tests/test_recording_flow.py`.
- Full suite: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./venv/bin/python -m pytest -q`.

## Follow-Ups

- Extract AI completion and dirty-state coordination without changing the widget's public signal contract.
