# SPEC-017: Stability Hardening And Failure Observability

Status: Completed
Owner: Runtime and application services
Last updated: 2026-09-10

## Problem

Long-running recording, transcription, RAG, summary, and import workflows can
fail at several native or asynchronous boundaries. The application must expose
recoverable failures, preserve user data, and release owned resources instead
of leaving silent partial states.

## Scope

- In scope: worker and subprocess lifecycle, terminal-state cleanup, error
  classification, user-visible recovery status, retry boundaries, temporary
  artifact cleanup, and characterization coverage for compatibility facades.
- Out of scope: changing transcription quality, replacing providers, redesigning
  the UI, or adding automatic recording stop behavior covered by SPEC-015.

## Current Implementation Context

The first implementation pass MUST start from these existing owners and contracts:

| Boundary | Current owner | Existing contract to preserve |
| --- | --- | --- |
| Audio capture | `src/audio.py` | `Recorder.start/pause/resume/stop`, `amplitude_changed`, WAV output |
| STT worker | `src/worker_components/transcriber_thread.py` | `finished`, `progress`, `status_update`, `error` Qt signals |
| Native STT process | `src/worker_components/subprocess_runner.py` | spawn isolation, interruption polling, timeout, process cleanup |
| Summary queue | `src/app/summary_queue/` and `src/ui/summary_queue/` | sequential execution, duplicate admission, queue status signals |
| RAG subprocesses | `src/rag/subprocess_tasks.py` | Windows-safe isolation and no unsafe in-process fallback |
| Window shutdown | `src/ui/main_window/window_lifecycle.py` | recorder, tabs, queue, floating chat, and worker cleanup ordering |
| Persistence façade | `src/database.py` over `src/persistence/` | existing imports and stored SQLite data |

The implementation MUST not create a second lifecycle owner for any row above.

## User Stories

### US1 - Recover from a failed background operation

As a user, when a background operation fails, I can see what failed, whether it
can be retried, and what data was preserved.

### US2 - Trust repeated lifecycle operations

As a user, repeated start, cancel, complete, and close operations do not leave
orphaned threads, processes, temporary files, audio streams, or stale UI state.

### US3 - Preserve configured runtime policy

As a user, recovery does not silently replace my selected backend, device,
compute type, or model unless an existing explicit fallback policy applies after
a real runtime failure.

## Acceptance Criteria

- Every worker and subprocess has one observable terminal outcome: succeeded,
  cancelled, failed, or timed out.
- A terminal outcome is emitted or persisted at most once, even when cleanup and
  cancellation race.
- Recoverable failures contain an actionable user-facing message and retain
  queued or persisted work.
- Cleanup is idempotent and releases Qt workers, subprocess handles, audio
  streams, temporary files, and GPU resources owned by the operation.
- Compatibility imports and existing Qt signal contracts remain valid.
- Focused tests cover failure, cancellation, timeout, retry, and repeated
  cleanup; cross-component flows use real Qt signals and temporary SQLite.

## Explicit Contracts

### Terminal outcome

Each operation has exactly one terminal outcome with this shape at the
application boundary:

```text
status: succeeded | cancelled | failed | timed_out
operation_id: stable per execution
user_message: non-empty for failed/timed_out outcomes
retryable: boolean
preserved_work: boolean
```

Existing signal payloads remain compatible; adapters may map this contract onto
current signals before callers are migrated.

### Cleanup

Cleanup MUST be safe when called zero, one, or multiple times. It MUST:

- request interruption before terminating owned subprocesses;
- join/close processes and queues without waiting forever;
- stop and close an owned audio stream;
- disconnect or invalidate callbacks that can outlive the owner;
- remove only temporary artifacts created by that operation;
- release CUDA resources only when they were acquired by that operation.

### Recovery

Retry MUST be explicit at the admission boundary. A failed item remains
persisted or queued until a retry, discard, or successful replacement is
recorded. A retry MUST use the same configured backend/device/model unless the
existing provider fallback policy records a concrete runtime failure.

## Failure Matrix

| Failure | User-visible result | Preserve work | Retry |
| --- | --- | --- | --- |
| Provider returns an error | classified error and affected item | yes | yes |
| Native subprocess exit | crash/exit diagnostic | yes | yes, through existing fallback policy |
| Timeout | timeout diagnostic | yes | yes |
| User cancellation | cancellation status, no error toast | partial result only if explicitly persisted | yes |
| App shutdown | orderly cancellation/cleanup | queued/persisted items | on next launch where supported |
| Cleanup error | logged secondary diagnostic; original outcome retained | yes | no automatic duplicate retry |

## Non-Goals And Guardrails

- Do not turn every exception into a retry.
- Do not use `except Exception: pass` in a new lifecycle path.
- Do not report success before persistence and owned-resource cleanup have
  completed.
- Do not alter Windows subprocess isolation or GPU preference as a shortcut.

## Architecture Notes

- Keep policy in the smallest owning package under `src/app/`,
  `src/worker_components/`, or the relevant feature package.
- Use typed result/error categories at boundaries; do not replace failures with
  broad silent catches.
- Preserve `DBManager`, `RAGEngine`, and widget façades while migrating callers.
- Audit `src/ui/main_window/window_lifecycle.py`, transcription workers,
  summary queue workers, RAG subprocess tasks, and audio capture as separate
  lifecycle owners.

## Test Plan

- Unit: terminal-state transitions, error classification, cleanup idempotency,
  retry eligibility, and temporary artifact ownership.
- Integration: recording/transcription and summary queue lifecycles with real
  Qt signals, temporary SQLite, deterministic external-provider doubles, and
  explicit post-terminal resource assertions.
- Stress: repeated lifecycle operations and shutdown races under the existing
  stress marker.

Required integration cases:

1. transcription success, provider failure, timeout, interruption, and repeated
   `wait/cleanup`;
2. summary queue failure followed by another queued item;
3. application shutdown while a worker is active;
4. RAG subprocess failure without an unsafe in-process retry on Windows policy;
5. recorder stop after empty input and after a normal captured buffer.

## Refactor Notes

- Coordinate with SPEC-015 and SPEC-016; do not duplicate recording guardian or
  performance measurement responsibilities.
