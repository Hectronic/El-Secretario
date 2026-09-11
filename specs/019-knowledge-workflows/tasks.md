# Tasks: Reliable Knowledge Workflows

- [ ] T001 Characterize current indexing, search, chat context, summary, and task continuation.
- [ ] T002 Define persisted source fingerprints, status transitions, provenance, and retry contracts.
- [ ] T003 Implement incremental and idempotent indexing with durable status.
- [ ] T004 Implement degraded-search diagnostics and source provenance.
- [ ] T005 Add resumable summary/task continuation without duplicate results.
- [ ] T006 Add SQLite/RAG/AI integration coverage including restart recovery.
- [ ] T007 Update user-facing documentation and measure workflow impact.

## Definition of Done

- Existing RAG façade methods and result compatibility are preserved.
- Status and retry state survive application restart.
- Idempotency and failed-reindex preservation are proven with temporary SQLite
  and deterministic vector-store doubles.
- Chat, summaries, and tasks retain source/date/week provenance through retries.
- Degraded search is distinguishable from a successful semantic search.
