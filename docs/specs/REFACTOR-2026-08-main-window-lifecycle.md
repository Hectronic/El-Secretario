# REFACTOR-2026-08-LIFECYCLE: Main-Window Lifecycle And Navigation

Status: Implemented
Last updated: 2026-08-31

## Goal

Complete the `MainWindow` feature extraction by moving its remaining lifecycle work and small sidebar-navigation decisions to focused coordinators.

## Behavior Contract

- Preserved: shutdown order for search work, summary queue, tabs, floating chats, recorder, and optional GPU cache; palette and resize updates for floating chat; notebook/tag navigation and tag-filter synchronization.
- Preserved: Qt may deliver `changeEvent` or `resizeEvent` while `MainWindow` is still being constructed, so the Qt adapters safely no-op until the lifecycle coordinator is installed.
- Preserved: `open_selected_tag_chat()` calls the public `open_collection_chat()` extension point for existing callers and tests.
- Changed: none.

## Moved Boundaries

- From: `src/ui/main_window/__init__.py` event handling, `closeEvent` cleanup, and residual navigation decisions.
- To: `src/ui/main_window/window_lifecycle.py` and `src/ui/main_window/window_navigation.py`.
- Compatibility: `MainWindow` retains Qt event methods and public delegates as thin adapters.

## Specs Affected

- SPEC-001: Audio Capture And Import.
- SPEC-007: Chat Sessions, Context Builder, And Floating Chat.
- SPEC-008: Active Chat Context Sidebar.
- SPEC-009: Calendar Navigation And Date-Filtered Context.
- SPEC-010: Collections/Tags And Notebooks.
- SPEC-011: Summaries And Background Queue.

## Tests

- Focused: `tests/ui/main_window/test_window_lifecycle.py`, `tests/ui/main_window/test_window_navigation.py`, `tests/test_shutdown_cleanup_stress.py`, `tests/test_calendar_button.py`, and `tests/test_welcome_daily_summary_button.py`.
- Full suite: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./venv/bin/python -m pytest -q`.

## Closure

`MainWindow` is now the application composition root and Qt/compatibility facade. Further reductions require explicit caller migrations rather than moving another feature boundary out of it.
