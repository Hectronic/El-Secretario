# REFACTOR-2026-08: Main-Window Summary Queue Status

Status: Implemented
Last updated: 2026-08-29

## Goal

Reduce `MainWindow` orchestration by isolating the summary queue's status-bar presentation and completion-driven view synchronization.

## Behavior Contract

- Preserved: queue status labels, runtime metrics, progress behavior, queue-tab reuse, queue signal handling, and refresh of recording, summary, calendar, and sidebar views after queue completion.
- Changed: none.
- Out of scope: queue scheduling, worker lifecycle, task payloads, and the RAG runtime setup still owned elsewhere.

## Moved Boundaries

- From: `src/ui/main_window/__init__.py` queue status methods.
- To: `src/ui/main_window/summary_queue_status.py` (`SummaryQueueStatusCoordinator`).
- Compatibility: `MainWindow` retains the prior methods as delegates, including the early-startup status-message path.

## Specs Affected

- SPEC-011: Summaries And Background Queue.

## Tests

- Focused: `tests/ui/main_window/test_summary_queue_status.py`, `tests/test_main_window_status_message.py`, `tests/test_welcome_daily_summary_button.py`, `tests/test_summary_task_queue_integration.py`, and `tests/test_queue_management_widget.py`.
- Full suite: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./venv/bin/python -m pytest -q`.

## Follow-Ups

- Extract startup daily/weekly summary scheduling separately from the main-window shell.
- Continue moving notebook, search, settings, collections, and calendar coordination from `MainWindow` into focused coordinators.
