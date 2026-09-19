# SPEC-029: SQL Repositories Decoupling

Status: Implemented and validated
Owner: Héctor Álvarez López <hector.alvarez@diagroup.com>
Last updated: 2026-09-19

## Product contract
- `DBManager` remains the public compatibility API for the application database.
  It owns only the SQLite connection, schema initialization, compatibility helpers,
  and instantiated aggregate repositories; it contains no SQL statements.
- `RecordsRepository`, `TasksRepository`, `SummariesRepository`,
  `ChatSessionsRepository`, `TranscriptionLogsRepository`, `RAGIndexRepository`,
  and `QueueJobsRepository` own their aggregate SQL under `src/persistence/`.
  They receive a shared connection provider and can also be instantiated with a
  database path for isolated SQLite tests.
- `NotebookRepository` owns all notebook/entry schema and SQL. `NotebookDBManager`
  remains a backwards-compatible facade that delegates to it.
- Existing method names, argument behavior, return values, schema migrations,
  transaction boundaries, and SQLite row dictionaries remain compatible. Static
  `DBManager.compose_ai_text` and `init_db` remain available.
- A task repository reads only the minimal recording metadata it needs through its
  connection provider, so it stays usable without a `DBManager` instance.

## Acceptance and integration gate
This refactor crosses persistence and UI injection boundaries. Repository tests
run against temporary SQLite databases; facade tests verify instantiated delegates
and method routing. Existing `tests/integration/test_persistence_ports.py` proves
that real Qt note and batch widgets persist/query through the injected facade, and
`tests/integration/test_notebook_widget_persistence.py` proves the notebook UI
uses the delegated notebook store. External AI, audio, RAG and network edges are
not part of this refactor.
