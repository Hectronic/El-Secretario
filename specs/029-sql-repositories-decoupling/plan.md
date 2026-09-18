# Implementation Plan: SQL Repositories Decoupling

Status: Draft
Last updated: 2026-09-17
Spec: [spec.md](spec.md)

## Phases

### Phase 1: Aggregate Segmentation
- Create domain-focused modules under `src/persistence/`:
  - `recording_repository.py` (recordings, files, metadata)
  - `task_repository.py` (tasks, due dates, checklists)
  - `notebook_repository.py` (folders, text notes, folders list)
- Move raw SQL query structures into their respective repository classes.

### Phase 2: Facade Delegation
- Refactor `DBManager` constructor to instantiate the new repositories.
- Map existing `DBManager` method names to delegate internally to the appropriate repository (e.g. `DBManager.get_daily_summary` calls `RecordingRepository.get_daily_summary`).
- Maintain existing method parameters and return types exactly to preserve compatibility.

### Phase 3: Tests Refactoring
- Split `tests/test_database.py` into dedicated isolated tests under `tests/persistence/`.
- Verify that real SQLite interactions under offscreen mode remain fully validated.
