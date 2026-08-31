# REFACTOR-2026-08-RUNTIME: Main-Window Runtime Startup

Status: Implemented
Last updated: 2026-08-30

## Goal

Move runtime initialization and opt-in startup scheduling out of the main-window shell.

## Behavior Contract

- Preserved: RAG settings, safe-delete and subprocess flags, RAG propagation to open tabs, RAG disabled/error states, sensitive settings redaction in logs, and startup daily/weekly summary eligibility.
- Changed: none.
- Out of scope: RAG engine internals, queue worker lifecycle, and settings UI.

## Moved Boundaries

- From: `src/ui/main_window/__init__.py` RAG runtime, settings-log, and startup-summary methods.
- To: `src/ui/main_window/runtime_startup.py` (`RuntimeStartupCoordinator`).
- Compatibility: `MainWindow` retains delegates used by bootstrap and settings coordinators.

## Specs Affected

- SPEC-006: RAG Indexing And Semantic Search.
- SPEC-011: Summaries And Background Queue.

## Tests

- Focused: `tests/ui/main_window/test_runtime_startup.py`, `tests/ui/main_window/test_bootstrap.py`, `tests/ui/main_window/test_setup_actions.py`, `tests/test_welcome_daily_summary_button.py`, `tests/test_rag_engine.py`, and `tests/test_rag_fallback.py`.
- Full suite: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./venv/bin/python -m pytest -q`.

## Follow-Ups

- Extract settings, collections, notebook, and calendar coordination from the main-window shell.
- Keep RAG engine adapters as a separate refactor from this UI-runtime boundary.
