# SPEC-019: Reliable Knowledge Workflows

Status: Planned
Owner: RAG, summaries, chat, and task workflows
Last updated: 2026-09-10

## Problem

The application already supports transcription, semantic search, chat, summaries,
and task extraction, but users need clearer provenance, predictable indexing
state, and more useful continuation when knowledge workflows are partial or
stale.

## Scope

- In scope: indexing state, incremental reindexing, hybrid retrieval, source
  provenance, context diagnostics, summary/task continuation, and user-visible
  freshness status.
- Out of scope: new AI providers, replacing the vector store, changing model
  prompts without measurement, or broad UI redesign.

## Current Implementation Context

Current owners and compatibility boundaries are:

| Capability | Owner | Existing behavior |
| --- | --- | --- |
| RAG façade | `src/rag/engine.py`, `src/rag_engine.py` | `add_document`, `search`, `delete_document` |
| RAG writes | `src/rag/documents.py` | document metadata includes `id` and `deleted`; Windows may use subprocess |
| RAG search | `src/rag/search.py` | semantic search with keyword fallback |
| Chat context | `src/ui/chat/context_builder.py` and chat runtime | selected records/date/tags/notebook context |
| Summaries | `src/app/summaries/`, `src/app/summary_queue/` | persisted summaries and sequential queue |
| Tasks | `src/persistence/tasks.py`, `src/ui/tasks/` | record/day/week tasks, ordering, completion |
| Tools | `src/ui/tools/` | explicit reindex and data-management actions |

The existing `RAGEngine` and `DBManager` import paths MUST remain valid while
status/provenance storage is introduced.

## User Stories

### US1 - Know whether search is current

As a user, I can see whether a recording is indexed, pending, failed, or stale,
and can retry only the affected work.

### US2 - Trust chat context

As a user, chat answers identify the recordings and excerpts used, while an
empty or degraded search result explains why.

### US3 - Continue after partial processing

As a user, failed summary, task, or indexing work can resume without duplicating
successful results or losing persisted data.

## Acceptance Criteria

- Every indexed source has an observable status, last successful index time, and
  failure reason when applicable.
- Reindexing is incremental and idempotent for unchanged sources.
- Search can combine semantic and deterministic keyword fallback according to
  runtime policy and reports degraded mode.
- Chat context exposes source identity and sufficient provenance for the UI.
- Summary and task workflows retain successful partial results and support
  targeted retry.
- Persistence and queue state remain consistent after restart.

## Data Contract

Each source status record MUST be derivable from persisted data and contain:

```text
source_id: stable record/document identifier
content_fingerprint: deterministic hash of indexed content plus relevant metadata
status: pending | indexing | indexed | stale | failed
indexed_at: nullable timestamp
failure_code: nullable stable category
failure_message: nullable safe user-facing detail
attempts: non-negative integer
```

The existing vector document ID remains the source identity; no second opaque
identity may be introduced without a migration plan.

Search results SHOULD carry:

```text
source_id, title/filename, excerpt, score, retrieval_mode, indexed_at
```

`retrieval_mode` is `semantic` or `keyword_fallback`, allowing the UI and chat
runtime to explain degraded operation without treating fallback as success of
semantic retrieval.

## Idempotency And Freshness Rules

- Same `source_id` and unchanged fingerprint: no re-embedding or duplicate
  vector write.
- Changed fingerprint: mark `stale`, then replace the existing document
  atomically from the caller's perspective.
- Failed indexing: retain the prior indexed version when one exists; expose the
  new failure separately.
- Delete: preserve the existing safe-delete policy and make status terminal only
  after the selected delete operation succeeds.
- Retry: target only failed/stale sources selected by the user or queue policy.

## Provenance Rules

- Context builders must retain source identity while formatting excerpts.
- Chat answers must be able to list the source records used, even when the
  provider returns no citations.
- Empty results distinguish “no matching content”, “no indexed sources”, and
  “search degraded/failed”.
- Summaries and tasks keep their record/date/week association when retried.

## Architecture Notes

- Keep document mutation and search policy under `src/rag/`; keep summaries and
  queue orchestration under `src/app/`.
- Store provenance and status through persistence repositories rather than UI
  state.
- Preserve Windows subprocess safety and configured embedding/runtime policy.
- Reuse existing chat context, summary queue, task board, and tools boundaries.

## Test Plan

- Unit: indexing fingerprints, status transitions, hybrid ranking/fallback,
  provenance shaping, and idempotent retry decisions.
- Integration: temporary SQLite plus deterministic RAG/AI doubles across
  recording → indexing → search/chat and summary/task continuation.
- Restart: recover pending/failed work without duplicating persisted results.

Required integration cases:

1. record content → index → search with source identity retained;
2. unchanged record does not cause a second vector write;
3. changed record replaces the old content and status;
4. failed reindex preserves a previously indexed version;
5. semantic failure produces deterministic keyword fallback metadata;
6. queue restart resumes pending work without duplicate summaries/tasks;
7. deletion follows the platform safe-delete policy and updates status.

## Refactor Notes

- Performance thresholds and measurements belong in SPEC-016.
- Failure and cleanup contracts belong in SPEC-017.
