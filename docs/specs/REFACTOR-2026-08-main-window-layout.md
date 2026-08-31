# REFACTOR-2026-08-LAYOUT: Main-Window Layout Composition

Status: Implemented
Last updated: 2026-08-31

## Goal

Move the visual construction of the main application window out of the `MainWindow` compatibility shell.

## Behavior Contract

- Preserved: the three-pane layout, central tabs, calendar, history, task, chat-context, tags, notebooks, settings, and floating-chat controls.
- Changed: none.
- Out of scope: changing visual design, widget behavior, signals, or platform-specific UI behavior.

## Moved Boundary

- From: `MainWindow.init_ui()` in `src/ui/main_window/__init__.py`.
- To: `build_main_window_layout()` in `src/ui/main_window/layout.py`.
- Compatibility: `MainWindow.init_ui()` remains a delegating entry point for existing startup code and integrations.

## Specs Affected

- SPEC-001: Audio Capture And Import.
- SPEC-004: Recording Metadata, Notes, Favorites, And Deletion.
- SPEC-007: Chat Sessions, Context Builder, And Floating Chat.
- SPEC-008: Active Chat Context Sidebar.
- SPEC-009: Calendar Navigation And Date-Filtered Context.
- SPEC-010: Collections/Tags And Notebooks.
- SPEC-011: Summaries And Background Queue.
- SPEC-012: Task Extraction And Task Board/Sidebar.
- SPEC-013: Settings, Secrets, Prompts, Theme, RAG Config.

## Tests

- Focused: `tests/ui/main_window/test_layout.py`, the remaining `tests/ui/main_window/` suite, `tests/test_recording_flow.py`, and `tests/test_welcome_daily_summary_button.py`.
- Full suite: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./venv/bin/python -m pytest -q`.

## Follow-Ups

- Replace `MainWindow` legacy wrappers with direct coordinator calls only when all external callers have migrated.

## Closure Audit

- `MainWindow` no longer contains visual construction or feature-specific tab, sidebar, chat, recording, queue-status, RAG-startup, search, setup, or selection-sync logic.
- It retains only window construction/wiring, Qt event adapters (`changeEvent`, `closeEvent`, `resizeEvent`), small navigation adapters, and compatibility delegates required by existing Qt signals and integrations.
- The lifecycle extraction is recorded separately in `REFACTOR-2026-08-LIFECYCLE`; no further `MainWindow` code should be moved unless a compatibility caller can migrate safely.
