# Implementation Plan: Runtime Performance Baseline

**Branch**: `016-runtime-performance-baseline` | **Status**: Planned | **Spec**: [spec.md](spec.md)

## Summary

Establish profiling and repeatable performance tests before changing code. Select
only evidence-backed fixes in UI update cadence, capture buffers, worker cleanup,
RAG reuse, or queue scheduling; retain existing STT/AI runtime policy.

## Measurement Scope

- Capture: callback/buffer growth and UI update frequency.
- Workers: thread/model lifetime, cancellation, and temporary artifacts.
- UI: main-event-loop latency during recording, queue, and transcription status.
- RAG: repeated initialization, indexing/search work, and fallback behavior.

## Existing Hotspot Hypotheses To Validate

These are hypotheses, not accepted findings:

- `src/audio.py` retains every callback block until stop and concatenates the
  complete recording in memory.
- `src/rag/chroma_store.py` creates an embedding function during store setup.
- `src/worker_components/subprocess_runner.py` polls and joins native processes
  during cancellation and timeout.
- `src/ui/main_window/` may duplicate sidebar refresh work across coordinators.
- The sequential summary queue may spend time rebuilding status views.

The first benchmark report must confirm or reject each hypothesis before code
changes are proposed.

## Acceptance Threshold Policy

Before the baseline exists, use no universal target. For each accepted
optimization, define a local threshold using timing, memory, UI responsiveness,
and correctness comparisons against the paired baseline.

## Constitution Check

Every optimization must be reversible, benchmarked, regression-tested, and
cross-platform safe. No quality/runtime preference may be changed merely to make
a benchmark look better.
