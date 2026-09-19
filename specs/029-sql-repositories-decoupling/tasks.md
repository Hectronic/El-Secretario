# Tasks: SQL Repositories Decoupling

Status: Implemented and validated
Last updated: 2026-09-19

- [x] T001 Establish domain repositories for records, tasks, summaries, chats,
  transcription logs, RAG index, queue jobs, and notebooks.
- [x] T002 Relocate direct SQL from `DBManager` and `NotebookDBManager` into the
  repository modules.
- [x] T003 Refactor both managers into backwards-compatible delegate facades.
- [x] T004 Split `test_database.py` into focused `tests/persistence/` suites and
  relocate note-widget tests to `tests/ui/notes/`.
- [x] T005 Add facade routing and standalone repository SQLite coverage.
- [x] T006 Run focused integration tests, the full suite, and Karate contracts.
