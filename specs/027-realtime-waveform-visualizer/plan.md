# Implementation Plan: Real-Time Audio Waveform Visualizer

Status: Implemented and validated
Last updated: 2026-09-18
Spec: [spec.md](spec.md)

## Ownership and implementation
- Add the visualizer to the existing `recording_in_progress` feature package;
  no file moves, compatibility shims, new dependencies or capture changes.
- Keep a bounded deque of normalized RMS display levels. Paint cubic segments
  with horizontal control tangents so interpolated levels cannot overshoot.
- Use the live widget palette and responsive maximum widths in the layout.
- Feed levels through the capture widget's decorated Qt slot. Connect pause and
  cleanup to the visualizer's parent-owned, finite-duration decay timer.
- Update existing layout/lifecycle tests to assert waveform outcomes instead of
  progress-bar values. Add widget tests and real-signal integration contracts.
- Update all three README languages. No additional refactor follow-up required.

## Validation
`QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest -q tests/ui/recording_in_progress tests/test_recording_in_progress_layout.py tests/integration/test_recording_in_progress_lifecycle.py`

`QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest -q`

## Results (2026-09-18)
- Focused: 36 passed.
- Full suite: 887 passed, 1 skipped (system tray unavailable), 11 subtests passed.
- Initial full collection was blocked by the missing declared `mcp<2` dependency;
  installed it with `./.venv/bin/python -m pip install 'mcp<2'`, then reran successfully.
- Rendered the widget under Light, Dark and SNES; inspected the Dark capture.
- `git diff --check` passed. No files moved; layout and lifecycle wiring updated.
- Validation ran on Linux with Qt offscreen; native Windows/macOS UI behavior
  and physical audio input were not exercised.
