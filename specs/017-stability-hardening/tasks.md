# Tasks: Stability Hardening

- [ ] T001 Inventory worker, subprocess, stream, queue, and temporary-file ownership.
- [ ] T002 Add characterization tests for success, failure, cancellation, timeout, and shutdown races.
- [ ] T003 Define typed terminal outcomes and user-facing error categories.
- [ ] T004 Harden transcription, summary queue, RAG subprocess, and capture cleanup.
- [ ] T005 Preserve queued/persisted work across recoverable failures and retries.
- [ ] T006 Add Qt/SQLite integration coverage for terminal lifecycle contracts.
- [ ] T007 Run stress coverage and verify Windows, Ubuntu, and macOS guards.

## Definition of Done

- No new broad silent catches exist in touched paths.
- Every changed boundary has a focused test and, where applicable, a real Qt /
  SQLite integration test.
- Repeated cleanup and shutdown-race tests pass without leaked workers,
  subprocesses, streams, or operation-owned temporary files.
- Existing public imports and signal payloads remain compatible.
