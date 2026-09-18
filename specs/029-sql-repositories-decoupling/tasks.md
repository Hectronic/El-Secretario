# Tasks: SQL Repositories Decoupling

Status: Draft
Last updated: 2026-09-17

- [ ] T001 Design and write domain aggregate repositories (`recording_repository`, `task_repository`, `notebook_repository`).
- [ ] T002 Relocate raw SQLite SQL statement strings from `DBManager` into repositories.
- [ ] T003 Refactor `DBManager` to act strictly as a backwards-compatible delegate facade.
- [ ] T004 Split the monolithic database test suite into focused tests under `tests/persistence/`.
- [ ] T005 Execute full integration and Karate tests to verify complete backward contract compatibility.
