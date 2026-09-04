# REFACTOR-2026-09-WELCOME-LAYOUT: Welcome Visual Layout

Status: Implemented
Last updated: 2026-09-05

## Behavior Contract

- Preserve the welcome screen's controls, signals, clock header, scroll container,
  responsive density, and Windows-specific compact-layout threshold.
- Preserve the resource lookup used by packaged and development builds on Windows,
  Ubuntu, and macOS.

## Moved Boundary

- From: visual construction and responsive sizing in `src/ui/welcome_widget.py`.
- To: `src/ui/welcome/layout.py`.
- `WelcomeWidget` remains the Qt signal façade and delegates construction and sizing
  to the layout module.

## Tests

- Focused: `tests/ui/welcome/`, `tests/test_welcome_daily_summary_button.py`.
- Full suite: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./venv/bin/python -m pytest -q`.
