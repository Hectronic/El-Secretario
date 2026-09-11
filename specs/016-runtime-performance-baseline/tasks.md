# Tasks: Runtime Performance Baseline

## Phase 1: Measure

- [x] T001 Define representative capture, transcription, RAG, queue, UI, and shutdown scenarios.
- [x] T002 Add reproducible profiling/benchmark harnesses with documented baselines.

## Phase 2: Diagnose

- [x] T003 Identify and rank the capture UI signal flood as the selected hotspot; defer unmeasured hypotheses.
- [x] T004 Cap only capture UI signals at 20 Hz; retain PCM buffers and all configured runtime policy.

## Phase 3: Optimize and Verify

- [x] T005 Implement the measured UI cadence improvement without changing capture/STT semantics.
- [x] T006 Add focused capture regression coverage; existing Qt lifecycle integration continues to prove UI boundary cleanup.
- [x] T007 Compare callback/update counts and validate platform-neutral Python/Qt guards.
- [x] T008 Run the full suite and record the accepted performance results.

## Definition of Done

- The six representative scenarios have reproducible harnesses and baseline
  output.
- Hotspot hypotheses are ranked using measurements, not file size or intuition.
- Every optimization has a paired before/after result and regression test.
- Full-profile runtime policy and cross-platform guards remain unchanged.
