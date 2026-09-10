# SPEC-018: Lightweight Installation And Lazy Runtime

Status: Planned
Owner: Runtime bootstrap and integration boundaries
Last updated: 2026-09-10

## Problem

The current installation combines several heavyweight ML and native providers,
while application startup can initialize integrations before they are needed.
Users should be able to install and launch the core application without paying
the cost of unused transcription, diarization, embedding, or AI providers.

## Scope

- In scope: dependency profiles, optional provider installation, lazy imports,
  deferred RAG/embedding initialization, startup diagnostics, and clear missing
  capability messages.
- Out of scope: removing supported providers, changing model quality, changing
  default runtime policy, or optimizing measured hot paths covered by SPEC-016.

## Current Implementation Context

The repository currently has one flat `requirements.txt` and no packaging
metadata that defines optional extras. The main eager/heavy boundaries are:

- `src/worker_components/device_selection.py` and runtime helpers importing
  Torch;
- `src/worker_components/transcriber_thread.py` importing Torch and Qt;
- `src/rag/engine.py` importing Chroma at module load;
- `src/rag/chroma_store.py` creating an embedding function during engine setup;
- `src/audio.py` importing `sounddevice`, `soundfile`, and NumPy;
- provider modules under `src/ai_providers/` and `src/stt_providers/`.

The full installation represented by the current `requirements.txt` MUST remain
supported. The first change MUST preserve `run.sh`, Windows scripts, CI, and
the documented `./venv/bin/python -m pytest` workflow.

## User Stories

### US1 - Install only what I need

As a user, I can install a core profile and add STT, RAG, diarization, or AI
capabilities without installing unrelated heavyweight stacks.

### US2 - Launch quickly

As a user, the application reaches its usable UI without initializing unused
providers or downloading/loading models.

### US3 - Understand unavailable capabilities

As a user, selecting an unavailable capability gives a precise installation or
configuration action rather than an import traceback.

## Acceptance Criteria

- A documented core installation starts without importing unused heavyweight
  providers.
- Each optional capability declares its dependencies and a supported install
  path.
- RAG stores, embedding functions, STT engines, diarization, and AI providers
  initialize only when their capability is requested.
- Missing optional dependencies produce a stable, user-facing diagnostic while
  core features remain usable.
- Existing full installations retain the same provider choices, model behavior,
  persistence, and compatibility imports.
- Startup and first-use measurements demonstrate lower cold-start cost without
  regressing first-use behavior.

## Proposed Capability Profiles

The implementation should converge on these names unless measurement or
packaging constraints justify a documented alternative:

| Profile | Provides | Must not require |
| --- | --- | --- |
| `core` | PyQt, SQLite, settings, metadata, basic UI | Torch, Chroma, Whisper, pyannote |
| `audio` | recording/import/edit metadata | ML model packages |
| `stt` | faster-whisper, openai-whisper, Sherpa adapters | pyannote |
| `diarization` | pyannote and compatible Torch runtime | RAG/AI providers |
| `rag` | Chroma, embeddings, search | diarization |
| `ai` | Gemini and Ollama adapters | local STT |
| `dev` | pytest, pytest-qt, all supported test dependencies | — |

These are installation boundaries, not feature toggles: a full install must
still expose all existing settings and provider choices.

## Capability Diagnostic Contract

When an optional dependency is missing, the provider boundary returns a stable
diagnostic containing:

```text
capability: stt | diarization | rag | ai | audio
provider: configured provider name
missing_packages: sorted list
install_hint: documented profile or command
user_message: actionable and non-technical summary
```

Import errors MUST not be swallowed as a generic provider failure, and the
diagnostic MUST be available without importing the missing provider again.

## Lazy-Initialization Invariants

- Importing the application bootstrap MUST NOT create a Chroma client, embedding
  model, Whisper model, pyannote pipeline, or AI client.
- Constructing `RAGEngine` retains its public API, but actual embeddings may be
  deferred until the first indexing/search operation.
- Selecting a provider is configuration-only; provider construction occurs at
  first use.
- A failed first-use initialization is retryable after the user fixes settings
  or installs the capability.
- A full installation produces the same persisted data and provider selection
  behavior as today.

## Architecture Notes

- Keep provider factories and runtime policy as the integration boundary.
- Prefer import guards and dependency checks at provider entry points, not
  scattered UI conditionals.
- Keep PyQt, SQLite, basic audio metadata, and core persistence in the base
  profile.
- Define profiles for STT, diarization, RAG, AI, and development/testing in
  repository documentation and packaging configuration.

## Test Plan

- Unit: capability detection, dependency diagnostics, provider factory loading,
  and lazy initialization.
- Integration: core startup and first-use flows with unavailable optional
  providers simulated at the import boundary.
- Compatibility: full dependency profile provider contracts and existing
  cross-platform startup scripts.

Required measurements:

1. fresh-process import time for core bootstrap;
2. time and peak RSS until the first usable window;
3. first-use time and peak RSS for STT, RAG, AI, and diarization separately;
4. installed-package size per profile.

Thresholds MUST be recorded after a baseline exists in SPEC-016; no arbitrary
threshold may be used to justify a behavior regression.

## Refactor Notes

- Measurements and accepted thresholds belong in SPEC-016.
- Runtime cleanup and failure semantics belong in SPEC-017.
