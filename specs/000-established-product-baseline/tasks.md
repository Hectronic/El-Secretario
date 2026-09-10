---
description: "Completed task list for the established product baseline"
---
# Tasks: Established Product Baseline

**Input**: [spec.md](spec.md) and [plan.md](plan.md)  
**Status**: All baseline tasks implemented and converged on 2026-09-10.

## Phase 1: Foundation

- [x] T001 Establish the PyQt desktop application, SQLite persistence, logging, and cross-platform startup.
- [x] T002 Create compatible façade boundaries and aggregate-specific persistence repositories.
- [x] T003 Define the project constitution, mandatory virtualenv test gate, and integration-test policy.

## Phase 2: User Story 1 - Capture, Transcribe, and Edit

- [x] T004 [US1] Implement audio capture/import, recording lifecycle, and safe file handling.
- [x] T005 [US1] Implement STT/diarization adapters with backend/device/compute policy and cleanup.
- [x] T006 [US1] Implement waveform editing, preview, backup-safe persistence, and retranscription.
- [x] T007 [US1] Add unit/UI tests and real SQLite editor lifecycle integration coverage.

## Phase 3: User Story 2 - Organize and Retrieve Work

- [x] T008 [US2] Implement recordings, notes, tags, collections, notebooks, calendar, and sidebar synchronization.
- [x] T009 [US2] Implement RAG document mutation, search, safe fallbacks, and compatible engine façade.
- [x] T010 [US2] Add persistence, calendar, notebook, sidebar, and RAG integration contracts.

## Phase 4: User Story 3 - Assistance and Summaries

- [x] T011 [US3] Implement chat context, sessions, floating lifecycle, and standalone chat compatibility.
- [x] T012 [US3] Implement provider validation, summary generation, queue execution, and worker lifecycle boundaries.
- [x] T013 [US3] Add real SQLite/Qt integrations for sessions, providers, summary generation, and queues.

## Phase 5: User Story 4 - Tasks, Tools, and Settings

- [x] T014 [US4] Implement task boards, extracted-task persistence, tools, export/import, maintenance, and settings panels.
- [x] T015 [US4] Add integration coverage for task, tool, provider, and data-transfer boundaries.

## Phase 6: Polish and Convergence

- [x] T016 Refactor broad UI/runtime areas into focused owner packages while retaining required façades.
- [x] T017 Document capability contracts, module ownership, and tests in Spec Kit artifacts.
- [x] T018 Run focused tests, integration tests, full suite, and formatting/link checks for the closing refactors.
- [x] T019 Record that no structural hotspot is currently confirmed; defer only evidence-backed follow-up work.

## Dependencies & Execution Order

All listed work is complete. Foundation preceded feature slices; each feature slice
was independently testable; cross-cutting polish followed implementation. Future
work starts as a new numbered Spec Kit feature directory and follows the same
specification → plan → tasks → implementation → convergence flow.
