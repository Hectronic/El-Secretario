# Feature Specification: Runtime Performance Baseline

**Feature Branch**: `016-runtime-performance-baseline`  
**Created**: 2026-09-10  
**Status**: Completed

**Input**: Improve responsiveness and resource use through evidence, without
reducing transcription quality or overriding user runtime choices.

## User Scenarios & Testing

### User Story 1 - Keep the UI responsive during long work (Priority: P1)

As a user, recording, transcription, indexing, and queue activity do not make
the interface visibly stall during normal interaction.

**Acceptance Scenarios**:

1. **Given** a long-running worker, **When** the user navigates or updates UI
   controls, **Then** UI work remains on the Qt event loop and heavy work remains
   off it.

### User Story 2 - Avoid avoidable resource growth (Priority: P1)

As a user, prolonged capture and repeated workers do not retain buffers, temporary
files, models, or threads beyond their useful lifetime.

**Acceptance Scenarios**:

1. **Given** repeated lifecycle operations, **When** they complete, **Then**
   workers, temporary artifacts, and owned resources are released.

### User Story 3 - Preserve configured quality and runtime policy (Priority: P1)

As a user, performance changes retain my selected STT backend/device/compute type
and only use a safe fallback after a real runtime failure.

## Requirements

- **FR-001**: The work MUST begin with reproducible measurements and a baseline.
- **FR-002**: The work MUST target UI update frequency, bounded buffers, worker
  lifecycle, and avoidable repeated computation before algorithmic quality changes.
- **FR-003**: The work MUST not force CPU or downgrade selected model/backend as
  a performance shortcut.
- **FR-004**: Each accepted optimization MUST retain focused regression coverage;
  shared boundary changes require integration coverage.

## Measurement Contract

Every result records operating system, Python version, provider/model
configuration, audio characteristics, warm/cold cache state, and whether the
external edge was real or deterministic. Record median and p95 timings plus
peak RSS where available.

| ID | Scenario | Primary metrics |
| --- | --- | --- |
| `startup` | fresh process to usable main window | time, imports, peak RSS |
| `capture` | deterministic 5/30-minute callback simulation | buffer bytes, callback rate, UI updates |
| `stt` | representative transcription | worker start, duration, cleanup latency, peak RSS |
| `queue` | N summary tasks with one failure | admission, idle latency, cleanup, retained state |
| `rag` | engine creation, first index, repeated search | init time, first-use time, repeated-call cost |
| `shutdown` | close while each operation is active | shutdown latency, remaining threads/processes |

The harness must not require a GPU, microphone, network, or AI provider.
Those edges use deterministic doubles; SQLite and Qt event delivery remain real.

## Baseline Output

Store machine-readable results outside source packages during development and
record accepted before/after summaries in this spec or its plan. Each result
includes:

```text
scenario, commit, platform, python, configuration, repetitions
median_ms, p95_ms, peak_rss_mb, observed_leaks, notes
```

No optimization is accepted from a single run or from wall-clock improvement
that increases memory, drops UI signals, changes result shape, or alters the
configured runtime policy.

## Success Criteria

- **SC-001**: Baseline measurements identify the dominant cost for each selected
  workflow before its implementation changes.
- **SC-002**: Chosen optimizations demonstrate a measurable improvement against
  that baseline with no behavioral regression.
- **SC-003**: Full tests and existing cross-platform guards remain green.

## Guardrails

- Do not benchmark with `force_cpu=true` unless selected by the configuration.
- Do not replace model/backend/device settings to improve a benchmark.
- Do not count hidden lazy initialization as an improvement if first-use cost
  regresses beyond the recorded baseline.
- Capture changes preserve WAV content, sample rate, channel count, and
  stop/cancel semantics.
