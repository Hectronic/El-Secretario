# Tasks: RAG Embeddings Cache

Status: Draft
Last updated: 2026-09-17

- [ ] T001 Design the SQLite caching schema and create the cache manager class inside `src/rag/`.
- [ ] T002 Implement SHA256 hashing computation on text chunks inside `RAGEngine`.
- [ ] T003 Code the cache lookup, hit interception, and database save logic.
- [ ] T004 Implement BLOB float-array serialization/deserialization for vector storage.
- [ ] T005 Write unit tests verifying hit ratios, zero inference calls during hits, and invalidation rules.
