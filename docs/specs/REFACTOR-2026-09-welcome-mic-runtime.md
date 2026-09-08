# REFACTOR-2026-09-WELCOME-MIC: Welcome Microphone Runtime

Status: Implemented
Last updated: 2026-09-04

## Behavior Contract

- Preserved: microphone discovery, rescan feedback, test stream lifecycle, RMS/VU updates, and safe stop before capture.
- Changed: none.

## Moved Boundary

- From: `src/ui/welcome_widget.py`.
- To: `src/ui/welcome/mic_runtime.py`.

## Tests

- Focused: `tests/ui/welcome/test_mic_runtime.py`, `tests/ui/welcome/test_mic_test.py`.
- Full suite: `QT_QPA_PLATFORM=offscreen ./venv/bin/python -m pytest -q`.
