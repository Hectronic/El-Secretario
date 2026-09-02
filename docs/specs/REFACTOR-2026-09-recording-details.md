# REFACTOR-2026-09-RECORD-DETAILS: Recording Detail Loading And Persistence

Status: Implemented
Last updated: 2026-09-01

## Goal

Move saved-record loading and user-initiated metadata persistence out of the recording detail widget.

## Behavior Contract

- Preserved: detail widgets display the selected recording, refresh tasks, configure audio availability, and reset dirty state after loading.
- Preserved: saving title, transcription, notes, tags, and diarization persists all fields, updates RAG when enabled, marks the tab clean, and emits existing saved/status signals.
- Changed: none.

## Moved Boundary

- From: `src/ui/recording_widget.py`.
- To: `src/ui/recording/record_details.py` (`RecordingDetailsCoordinator`).
- Compatibility: `RecordingWidget.load_record()` and `save_all_changes()` remain public delegates.

## Specs Affected

- SPEC-004: Recording Metadata, Notes, Favorites, And Deletion.
- SPEC-006: RAG Indexing And Semantic Search.

## Tests

- Focused: `tests/ui/recording/test_record_details.py`, `tests/test_recording_widget_ui.py`, `tests/test_recording_flow.py`, and `tests/ui/main_window/test_recording_tabs.py`.
- Full suite: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./venv/bin/python -m pytest -q`.

## Follow-Ups

- Extract direct-transcription completion and dirty-state coordination without changing queue or signal behavior.
