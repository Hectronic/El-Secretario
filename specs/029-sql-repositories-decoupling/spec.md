# SPEC-029: SQL Repositories Decoupling

Status: Draft
Owner: Héctor Álvarez López <hector.alvarez@diagroup.com>
Last updated: 2026-09-17

## Problem
Currently, database queries are managed by a single monolithic facade class `DBManager` in `src/database.py`. As El Secretario has grown, this facade has bloated with dozens of direct raw SQL queries covering recording metadata, transcription metrics, task boards, calendars, and notebook organization. This violates the Single Responsibility Principle, makes unit-testing specific database interactions hard, and complicates refactoring or migrating SQL logic.

## Proposal
Conclude the aggregate separation dictated by `GEMINI.md`. Extract all direct raw SQL statements out of the `DBManager` class and delegate them to domain-specific repository classes (e.g. `RecordingRepository`, `TaskRepository`, `NotebookRepository`) inside the `src/persistence/` package. The `DBManager` class will remain strictly as a backwards-compatible facade that delegates calls to these dedicated repositories.

### Key Highlights
- **Domain Repositories:** Segment persistence operations cleanly by domain aggregates under `src/persistence/`.
- **Decoupled Architecture:** Relocate all raw SQL strings and SQLite query executions from `DBManager` to repositories.
- **Facade Backward Compatibility:** Refactor `DBManager` to instantiate and delegate calls to domain repositories, ensuring zero regressions on the rest of the PyQt codebase.

## User Scenarios & Testing
- **Scenario:** Developer modifies the schema or SQL constraints for notebooks. They only need to edit `src/persistence/notebook_repository.py` and run its dedicated test file, leaving the rest of the database logic untouched.
- **Testing:** Relocate and split the existing database test suite (`tests/test_database.py` and `tests/test_notes.py`) into focused repository unit tests (`tests/persistence/test_recording_repo.py`, `test_task_repo.py`, etc.), validating query results and database schemas in isolation.
