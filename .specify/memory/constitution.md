# El Secretario Constitution

## Core Principles

### I. Preserved user contracts

Refactors preserve public imports, Qt signals, stored SQLite data, and configured
runtime behavior unless an approved feature specification explicitly changes them.

### II. Tests are non-negotiable

Every code change has focused tests. Changes crossing UI/signals, persistence,
workers, queues, STT, AI/RAG adapters, or platform behavior have real integration
coverage and run the full suite using the project virtual environment.

### III. Smallest owning boundary

New behavior belongs in the narrowest feature package or persistence aggregate.
Compatibility facades are retained only where callers need them.

### IV. Cross-platform desktop operation

Windows, Ubuntu, and macOS are supported. Qt ownership, subprocesses, paths,
audio devices, and runtime guards must remain portable.

### V. Runtime and resource safety

Configured transcription backend/device/compute preferences are respected. GPU
resources and worker threads are explicitly cleaned up, and recoverable failures
produce user-facing messages without losing queued or persisted work.

## Quality Gates

- Run `./venv/bin/python -m pytest` (or the documented local fallback), never
  system Python.
- Use temporary SQLite databases and offscreen Qt for integration tests; only
  external network, AI, STT, RAG, and audio hardware may be deterministic doubles.
- Keep feature artifacts in `specs/<NNN-feature>/` synchronized with behavior.

## Governance

This constitution governs future feature plans and tasks. Amendments require an
explicit update to this file and the affected feature artifacts.

**Version**: 1.0.0 | **Ratified**: 2026-09-10 | **Last Amended**: 2026-09-10
