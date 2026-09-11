# Tasks: Lightweight Installation And Lazy Runtime

- [ ] T001 Measure cold-start imports, startup time, and first-use initialization.
- [ ] T002 Map heavyweight dependencies to capability profiles and install paths.
- [ ] T003 Define capability detection and actionable missing-dependency diagnostics.
- [ ] T004 Defer STT, diarization, AI, embeddings, and RAG initialization until requested.
- [ ] T005 Preserve full-profile provider behavior and compatibility imports.
- [ ] T006 Add core-startup and optional-first-use integration coverage.
- [ ] T007 Update installation documentation for supported profiles and platforms.

## Definition of Done

- Core startup tests pass with optional provider imports unavailable.
- Full-profile provider and integration tests pass unchanged or with explicitly
  updated contracts.
- Every optional capability has one documented install path and one actionable
  diagnostic.
- Cold-start and first-use measurements are recorded before and after.
- README, Spanish, Asturian, Windows, and CI installation instructions agree.
