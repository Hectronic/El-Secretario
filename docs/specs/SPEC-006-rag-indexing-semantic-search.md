# SPEC-006: RAG Indexing And Semantic Search

Status: Implemented
Owner: TBD
Last updated: 2026-08-30

## Problem

Users need recordings, notes, summaries, and generated AI text to be searchable and reusable as chat context. Search must work when the persistent vector store is available, degrade predictably when it is not, and avoid returning soft-deleted content.

## Scope

- In scope: document upsert, semantic search, ID-restricted search, explicit metadata filters, soft-delete filtering, keyword fallback ranking, in-memory fallback storage, Chroma collection compatibility, and Windows subprocess safety paths for RAG upsert/query/delete.
- Out of scope: database record selection for reindex jobs, chat prompt construction, embedding model selection UI, cloud vector stores, and database schema redesign.

## User Stories

- As a user, I want saved content indexed so that later searches can find relevant recordings and notes.
- As a user, I want search results to respect filters so that date, tag, or caller-selected contexts stay narrow.
- As a user, I want deleted recordings excluded from search so that stale content is not reused.
- As a user on Windows, I want RAG operations to avoid native Chroma crash paths so that the desktop app remains stable.
- As a user, I want search to keep working with a deterministic fallback when persistent embeddings are unavailable.

## Acceptance Criteria

- Given non-empty text and metadata, when a document is indexed, then the stored metadata includes the document ID and `deleted=0`.
- Given empty text, when a document is indexed, then no document is added and no error is raised.
- Given a semantic query, when Chroma returns results, then the app returns result dictionaries containing `id`, `text`, `metadata`, and `distance`.
- Given semantic query results include metadata with `deleted=1`, when results are parsed, then those entries are omitted.
- Given a search receives explicit IDs, when the final Chroma `where` clause is built, then the IDs are combined with the deleted-content exclusion filter.
- Given a search receives an explicit metadata `where_clause`, when the final Chroma `where` clause is built, then it is combined with the deleted-content exclusion filter.
- Given persistent Chroma initialization fails, when `RAGEngine` starts, then it uses the in-memory fallback collection.
- Given a collection already exists with a conflicting embedding function, when it is opened, then the app retries without passing a new embedding function.
- Given Windows safe-delete mode is enabled, when a document is deleted, then the app writes a soft-delete marker instead of using Chroma's native delete path.
- Given Windows subprocess semantic query fails, when a later query runs in the same engine instance, then semantic subprocess queries are disabled and keyword fallback is used.
- Given keyword fallback ranks raw documents, when results are returned, then deleted entries are skipped and higher term-hit scores sort first with stable ordering for ties.

## Architecture Notes

- Public service: `src/rag_engine.py` keeps the public `RAGEngine` API used by UI, queue, and search integrations.
- Fallback store: `src/rag/fallback_store.py` owns the in-memory Chroma-compatible collection/client used when persistent Chroma cannot initialize.
- Result mapping: `src/rag/results.py` owns semantic result parsing and keyword fallback ranking.
- Filters: `src/rag/filters.py` owns deleted-content exclusion and ID/metadata filter composition.
- Chroma store: `src/rag/chroma_store.py` owns persistent-client initialization, in-memory fallback selection, embedding-function fallback, and collection creation.
- Chroma compatibility: `src/rag/chroma_compat.py` owns collection-open compatibility and sentencepiece/SWIG warning suppression.
- Subprocess safety: `src/rag/subprocess_tasks.py` owns Windows-safe subprocess entrypoints, timeout/crash/missing-result handling, and keyword fallback subprocess queries.
- Queue integration: `src/app/summary_queue/rag_reindex.py` selects records and calls the public RAG engine to index them.
- UI/search: `src/ui/main_window/search_actions.py` and `src/ui/search_results_widget.py` consume search results.
- Main-window runtime: `src/ui/main_window/runtime_startup.py` applies RAG safety flags, initializes or disables the engine from settings, and propagates the active engine to open tabs. `MainWindow` keeps compatibility delegates.
- Platform constraints: preserve Windows subprocess guards for upsert/query and safe-delete behavior; preserve Ubuntu persistent Chroma behavior.

## Test Plan

- Unit: filter composition, semantic result parsing, keyword ranking, in-memory collection matching/ranking, Chroma compatibility retry.
- Integration: `RAGEngine` initialization, add/search, restricted search, where-clause search, empty input, soft delete, hard delete, and fallback behavior.
- UI: search action opens search results without blocking the main window.
- Manual: index and search real recordings on Ubuntu and Windows, including Windows safe-delete and subprocess-query paths.

## Documentation

- Feature registry: `docs/specs/README.md`.
- Refactor record: `docs/specs/REFACTOR-2026-05-feature-packages.md`.

## Refactor Notes

- 2026-06-10: extracted in-memory fallback store, result parsing/ranking, filter composition, and Chroma compatibility helpers from `src/rag_engine.py` into `src/rag/`.
- 2026-06-10: extracted RAG subprocess entrypoints and JSON subprocess runner from `src/rag_engine.py` to `src/rag/subprocess_tasks.py`, with direct tests for success, operation error, missing result, crash, timeout, query, upsert, and keyword fallback wrappers.
- 2026-06-10: extracted Chroma client, embedding, fallback, and collection initialization from `RAGEngine.__init__` to `src/rag/chroma_store.py`, leaving `RAGEngine` as the public search/index/delete facade.
- 2026-06-10: removed private helper compatibility aliases from `src/rag_engine.py` after migrating legacy fallback tests to import helpers from their owning `src/rag/` modules.
- 2026-08-30: moved RAG runtime initialization and configuration propagation from `src/ui/main_window/__init__.py` to `src/ui/main_window/runtime_startup.py` without changing settings or platform safety flags.

## Open Questions

- Should subprocess integration tests exercise real Chroma subprocess query/upsert on Windows CI instead of only runner/wrapper behavior?
- Should a typed store adapter interface replace direct Chroma collection access before adding alternative vector stores?
