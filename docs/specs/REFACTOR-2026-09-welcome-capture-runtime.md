# REFACTOR-2026-09-WELCOME-CAPTURE: Welcome Capture Runtime

Status: Implemented
Last updated: 2026-09-05

## Behavior Contract

- Preserved: capture settings load/save, control wiring, mic-test stop before capture, optional device rescan, and recording/import signals.
- Changed: none.

## Moved Boundary

- From: `src/ui/welcome_widget.py`.
- To: `src/ui/welcome/capture_runtime.py`.

## Tests

- Focused: `tests/ui/welcome/test_capture_runtime.py`, `tests/ui/welcome/test_capture_state.py`.
- Full suite: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./venv/bin/python -m pytest -q`.
