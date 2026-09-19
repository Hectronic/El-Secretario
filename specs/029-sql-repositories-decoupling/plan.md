# Implementation Plan: SQL Repositories Decoupling

Status: Implemented and validated
Last updated: 2026-09-19
Spec: [spec.md](spec.md)

## Ownership
- `src/persistence/base.py`: connection provider, shared SQLite lifecycle and
  repository composition primitives.
- `src/persistence/{records,tasks,summaries,chats,logs,rag,queue}.py`: application
  database aggregates and their SQL.
- `src/persistence/notebooks.py`: notebook and entry schema plus SQL.
- `src/database.py` and `src/notebook_database.py`: compatibility facades only.

## Implementation
- Replace DBManager's multiple inheritance with instantiated repository delegates
  sharing one connection provider and schema lifecycle.
- Preserve method availability via forwarding methods, including `init_db`,
  `_week_sunday`, and static `compose_ai_text` compatibility helpers.
- Move notebook persistence SQL out of `NotebookDBManager`.
- Split legacy persistence tests into focused modules under `tests/persistence/`;
  move note-widget tests to `tests/ui/notes/`.

## Validation
Run focused repository tests, integration persistence contracts, and the full
PyQt offscreen suite with `./.venv/bin/python`.

## Results (2026-09-19)
- Focused persistence/UI integration: 35 passed.
- Full offscreen suite: 897 passed, 1 skipped (system tray unavailable), 11 subtests passed.
- Karate contract suite: 8 scenarios passed.
- Existing persistence-port integration coverage proves real Qt widgets persist through the injected facade and temporary SQLite databases.
- Files reshaped: `src/notebook_database.py` became a delegation facade; SQL moved to `src/persistence/notebooks.py`; monolithic persistence tests moved under `tests/persistence/`; note UI tests moved to `tests/ui/notes/`.
