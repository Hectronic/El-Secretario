# REFACTOR-2026-08-SHELL: Main-Window Shell Actions

Status: Implemented
Last updated: 2026-08-31

## Goal

Move the remaining outer-shell interactions out of `MainWindow` and remove duplicate sidebar-content behavior.

## Behavior Contract

- Preserved: welcome-screen navigation signals, accordion section state, task/chat-context refresh after tab changes, daily-summary request, history filtering, favorite persistence, and recording deletion behavior.
- Changed: none.
- Out of scope: visual construction of the main-window layout and individual feature-widget behavior.

## Moved Boundaries

- From: `src/ui/main_window/__init__.py` welcome wiring, accordion state, central-tab-change handling, daily-summary action, and duplicate sidebar-content actions.
- To: `src/ui/main_window/shell_actions.py`, `src/ui/main_window/runtime_startup.py`, and existing `src/ui/main_window/sidebar_content.py` owners.
- Compatibility: `MainWindow` retains delegates used by bootstrap, Qt signals, and existing integrations.

## Specs Affected

- SPEC-001: Audio Capture And Import.
- SPEC-004: Recording Metadata, Notes, Favorites, And Deletion.
- SPEC-011: Summaries And Background Queue.

## Tests

- Focused: `tests/ui/main_window/test_shell_actions.py`, `tests/ui/main_window/test_sidebar_content.py`, `tests/test_deletion.py`, `tests/test_welcome_daily_summary_button.py`, `tests/ui/main_window/test_bootstrap.py`, and `tests/ui/main_window/test_tab_lifecycle.py`.
- Full suite: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./venv/bin/python -m pytest -q`.

## Follow-Ups

- Remove legacy `MainWindow` compatibility wrappers only after their callers are migrated to the focused coordinators.
