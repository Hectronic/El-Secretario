# Tasks: RAG Embeddings Cache

Status: Implemented
Last updated: 2026-09-19

- [x] T001 Design the SQLite caching schema and create the cache manager class inside `src/rag/`.
- [x] T002 Implement SHA256 hashing computation on text chunks inside `RAGEngine`.
- [x] T003 Code the cache lookup, hit interception, and database save logic.
- [x] T004 Implement BLOB float-array serialization/deserialization for vector storage.
- [x] T005 Write unit tests verifying hit ratios, zero inference calls during hits, and invalidation rules.
