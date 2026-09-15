# Tasks: Lightweight Installation And Lazy Runtime

- [x] T001 Measure cold-start imports, startup time, and first-use initialization.
- [x] T002 Map heavyweight dependencies to capability profiles and install paths.
- [x] T003 Define capability detection and actionable missing-dependency diagnostics.
- [x] T004 Defer STT, diarization, AI, embeddings, and RAG initialization until requested.
- [x] T005 Preserve full-profile provider behavior and compatibility imports.
- [x] T006 Add core-startup and optional-first-use integration coverage.
- [x] T007 Update installation documentation for supported profiles and platforms.

## Definition of Done

- Core startup tests pass with optional provider imports unavailable.
- Full-profile provider and integration tests pass unchanged or with explicitly
  updated contracts.
- Every optional capability has one documented install path and one actionable
  diagnostic.
- Cold-start and first-use measurements are recorded before and after.
- README, Spanish, Asturian, Windows, and CI installation instructions agree.
