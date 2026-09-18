# SPEC-032: RAG Embeddings Cache

Status: Draft
Owner: Héctor Álvarez López <hector.alvarez@diagroup.com>
Last updated: 2026-09-17

## Problem
Every time text snippets or transcription chunks are added or re-indexed in the RAG database, the system must generate semantic vector embeddings. When using local inference providers (like Ollama), generating these embeddings is CPU and GPU intensive. If a user frequently saves minor edits to a note, or re-indexes existing recordings, the RAG engine redundantly recalculates identical vector embeddings for unchanged paragraphs. This slows down indexing speeds, wastes processor cycles, and increases VRAM heat.

## Proposal
Implement an extremely fast, lightweight RAG Embeddings Cache system. The RAG engine will calculate a unique SHA256 cryptographic signature/hash for each text paragraph/chunk before calling the embedding model. If the text hash already exists in a local persistent cache table, the system will instantly retrieve the cached vector from disk and bypass Ollama/inference entirely, accelerating re-indexing to milliseconds!

### Key Highlights
- **Cryptographic Text Hashing:** Generate SHA256 hashes for each text chunk to serve as unique cache lookup keys.
- **SQLite Cache Table:** Store calculated float vector arrays indexed by their SHA256 hash inside a lightweight SQLite cache table (`embeddings_cache.sqlite`).
- **Inference Bypassing:** Intercept RAG store additions; if a chunk has a cache hit, skip Ollama completely, reducing vector generation time from seconds to milliseconds.

## User Scenarios & Testing
- **Scenario:** The user makes a minor correction to a long note. During RAG save indexing, the note is chunked into 10 paragraphs. 9 paragraphs are unchanged, while 1 is modified. The RAG engine detects 9 cache hits, retrieves their vectors instantly, and only requests 1 embedding from Ollama. The entire save completes under 50ms instead of taking 3 seconds!
- **Testing:** Write unit tests demonstrating that repeated additions of identical text chunks result in zero model calls, verify correct vector representation floats serialization, and validate cache expiration/validation.
