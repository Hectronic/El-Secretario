# Implementation Plan: Runtime Performance Baseline

**Branch**: `016-runtime-performance-baseline` | **Status**: Completed and validated | **Spec**: [spec.md](spec.md)

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

The first benchmark report must select, reject, or defer each hypothesis before
code changes are proposed.

## Acceptance Threshold Policy

Before the baseline exists, use no universal target. For each accepted
optimization, define a local threshold using timing, memory, UI responsiveness,
and correctness comparisons against the paired baseline.

## Baseline And Accepted Optimization

Baseline command:

```bash
GIT_COMMIT=$(git rev-parse --short HEAD) ./venv/bin/python -m benchmarks.runtime_baseline --repetitions 7
```

The machine-readable result is stored at
`benchmarks/results/016-runtime-performance-baseline.json`. It records macOS,
Python 3.12.14, deterministic external edges, warm/cold state, retained runtime
policy, median/p95 timings, and peak RSS for startup, capture, STT, queue, RAG,
and shutdown. The startup scenario launches the real main window in a fresh
offscreen process; SQLite and Qt are real while provider/network edges are not.

The selected hotspot was capture's UI-facing RMS signal. At a 100 Hz callback
rate, the pre-change path would enqueue 30,000 updates in five minutes and
180,000 in thirty minutes. The accepted 20 Hz cap limits those counts to 6,000
and 36,000 respectively (80% fewer UI events), while the benchmarked capture
workload remains sub-millisecond and tests prove every PCM block is retained.
No STT backend, model, device, compute type, or `force_cpu` setting changed.

The other initial hypotheses were not accepted as optimizations: capture's PCM
buffer cannot be discarded without violating WAV semantics; RAG model setup,
subprocess cancellation, sidebar refresh, and queue rendering are deferred for
their own representative benchmarks rather than optimized by intuition.

## Constitution Check

Every optimization must be reversible, benchmarked, regression-tested, and
cross-platform safe. No quality/runtime preference may be changed merely to make
a benchmark look better.
