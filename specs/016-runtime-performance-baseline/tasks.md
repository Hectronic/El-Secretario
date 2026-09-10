# Tasks: Runtime Performance Baseline

## Phase 1: Measure

- [ ] T001 Define representative capture, transcription, RAG, queue, and UI scenarios.
- [ ] T002 Add reproducible profiling/benchmark harnesses with documented baselines.

## Phase 2: Diagnose

- [ ] T003 Identify and rank concrete hotspots from measured evidence.
- [ ] T004 Select the smallest safe optimization per hotspot and update the plan.

## Phase 3: Optimize and Verify

- [ ] T005 Implement only measured UI/buffer/worker/RAG/queue improvements.
- [ ] T006 Add focused regression and required real-boundary integration tests.
- [ ] T007 Compare before/after measurements and validate Windows, Ubuntu, macOS guards.
- [ ] T008 Run the full suite and record the accepted performance results.
