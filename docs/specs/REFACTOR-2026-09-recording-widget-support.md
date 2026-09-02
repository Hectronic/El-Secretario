# REFACTOR-2026-09-WIDGET-SUPPORT: Recording Widget Support

Status: Implemented
Last updated: 2026-09-01

## Goal

Complete `RecordingWidget`'s behavior extraction by moving dirty state, legacy trim support, audio source setup, and thread cleanup to a focused support module.

## Behavior Contract

- Preserved: unsaved-change state, safe trim/retranscribe behavior, audio availability controls, and worker cleanup.
- Changed: none.

## Moved Boundary

- From: `src/ui/recording_widget.py`.
- To: `src/ui/recording/widget_support.py`.
- Compatibility: the widget retains public slots and Qt lifecycle adapters.

## Tests

- Focused: `tests/ui/recording/test_widget_support.py`, `tests/ui/recording/test_audio_trim.py`, and `tests/test_recording_widget_ui.py`.
- Full suite: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./venv/bin/python -m pytest -q`.

## Closure

`RecordingWidget` is now a composition shell and compatibility facade; future feature changes should go to the focused `src/ui/recording/` modules.
