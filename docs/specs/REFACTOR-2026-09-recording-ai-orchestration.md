# REFACTOR-2026-09-AI-ORCHESTRATION: Recording AI Actions

Status: Implemented
Last updated: 2026-09-01

## Goal

Move recording-level AI action orchestration and queue-result refreshes out of the detail widget.

## Behavior Contract

- Preserved: summary/task queue requests, forced re-extraction, provider validation, legacy AI thread wiring, automatic post-transcription summaries, errors, and background refreshes.
- Changed: none.

## Moved Boundary

- From: `src/ui/recording_widget.py`.
- To: `src/ui/recording/ai_orchestration.py` (`RecordingAiCoordinator`).
- Compatibility: public widget slots remain delegating adapters and retain their existing dependency patch points.

## Specs Affected

- SPEC-004: Recording Metadata, Notes, Favorites, And Deletion.
- SPEC-011: Summaries And Background Queue.

## Tests

- Focused: `tests/ui/recording/test_ai_orchestration.py`, `tests/ui/recording/test_ai_actions.py`, and `tests/test_recording_widget_ui.py`.
- Full suite: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./venv/bin/python -m pytest -q`.

## Follow-Ups

- Extract dirty-state and legacy audio-editor coordination while preserving current UI signals.
