# Implementation Plan: Reliable Knowledge Workflows

**Branch**: `019-knowledge-workflows` | **Status**: Planned

## Summary

Add durable indexing and workflow status, then improve incremental retrieval,
provenance, and resumable summary/task processing while retaining current
provider and persistence compatibility.

## Phases

1. Characterize current indexing, search, summary, and task continuation.
2. Define persisted status, fingerprints, provenance, and retry contracts.
3. Implement incremental/idempotent indexing and degraded-search reporting.
4. Connect provenance and targeted continuation to chat, summaries, and tasks.

## Data-Migration Strategy

Prefer an additive SQLite migration with nullable/defaulted columns and a
backfill from existing records/documents. Do not require rebuilding the vector
store for application startup. Existing records without status are classified
as `pending` or `unknown` by an explicit migration rule, then indexed
incrementally.

## Ordering Constraints

1. Characterize current result shapes and fallback behavior.
2. Add persistence/status contracts before changing queue admission.
3. Add fingerprints before skipping any indexing work.
4. Add provenance to result objects before changing chat rendering.
5. Add restart recovery before claiming resumable workflows.

## Constitution Check

Uses existing persistence and integration boundaries, preserves runtime policy,
and requires real SQLite/Qt/provider-boundary integration coverage.
