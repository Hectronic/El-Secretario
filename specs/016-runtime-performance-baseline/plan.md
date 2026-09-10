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

## Constitution Check

Every optimization must be reversible, benchmarked, regression-tested, and
cross-platform safe. No quality/runtime preference may be changed merely to make
a benchmark look better.
