# Implementation Plan: RAG Embeddings Cache

Status: Implemented
Last updated: 2026-09-19
Spec: [spec.md](spec.md)

## Phases

### Phase 1: Cache Table Setup
- Create an SQLite cache schema with table `embeddings_cache` containing:
  - `text_hash` TEXT PRIMARY KEY (SHA256 signature)
  - `model_name` TEXT (e.g., nomic-embed-text)
  - `vector_data` BLOB (serialized float vector list)
- Integrate cache connection inside `src/rag/`.

### Phase 2: Interception Logic
- Update the `RAGEngine` vector generation routines.
- Calculate the SHA256 of the text combined with the embedding model name.
- Query the SQLite cache table. If a match is found, deserialize the BLOB back to a list of floats and return immediately.
- If missed, query Ollama/inference, save the resulting vector to the cache table, and return.

### Phase 3: Validation and Coverage
- Write tests asserting cache hits and misses, verifying zero inference calls during hits, and verifying correct vector deserialization.

## Delivered design
`EmbeddingsCache` persists model-scoped float vectors as SQLite BLOBs. `RAGEngine` resolves vectors through the cache before direct Chroma upserts, preserving subprocess safety paths. Focused RAG validation passes (`71 passed`); full suite completed successfully with exit code `0`.
