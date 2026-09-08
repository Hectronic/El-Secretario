# REFACTOR-2026-09-WELCOME-LANDING: Welcome Landing Actions

Status: Implemented
Last updated: 2026-09-05

## Behavior Contract

- Preserved: search requests, result navigation, favorites pagination, and today-list navigation.
- Changed: none.

## Moved Boundary

- From: `src/ui/welcome_widget.py`.
- To: `src/ui/welcome/landing_actions.py`.

## Tests

- Focused: `tests/ui/welcome/test_landing_actions.py`, `tests/ui/welcome/`,
  `tests/test_welcome_daily_summary_button.py`.
- Full suite: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./venv/bin/python -m pytest -q`.
