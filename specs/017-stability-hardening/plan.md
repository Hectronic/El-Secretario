# Implementation Plan: Stability Hardening

**Branch**: `017-stability-hardening` | **Status**: Completed and validated

## Summary

Establish lifecycle characterization tests, define terminal-state and error
contracts, then harden the highest-risk worker, subprocess, capture, queue, and
shutdown paths without changing configured runtime quality.

## Phases

1. Inventory ownership and add characterization tests before refactoring.
2. Introduce explicit terminal outcomes and actionable error categories.
3. Make cleanup and cancellation idempotent across worker and subprocess owners.
4. Verify recovery, shutdown, persistence, and cross-platform guards.

## Planned Deliverables

- A small, typed lifecycle/error vocabulary in the owning runtime package.
- Characterization tests before each behavior-preserving extraction.
- One cleanup owner per worker/process/stream; callers invoke it idempotently.
- A failure-to-UI/persistence mapping table for each queue and transcription
  boundary.
- A shutdown test that proves no owned worker or subprocess remains active.

## Ordering Constraints

1. Characterize current behavior before changing exception handling.
2. Harden process and worker cleanup before changing retry policy.
3. Change persistence or queue state only with restart/recovery integration
   coverage.
4. Keep SPEC-015 recording reminders separate from generic lifecycle cleanup.

## Constitution Check

Preserves public imports, Qt signals, SQLite data, runtime preferences, and
cross-platform behavior. Every boundary change requires real integration tests.

## Delivered Hardening

- `TerminalOutcome` provides a stable, typed one-shot contract for worker and
  queue outcomes while preserving existing Qt signal payloads.
- Transcription distinguishes success, cancellation, failure, and timeout;
  its terminal signal is emitted once even when interruption races completion.
- Native STT and RAG subprocess owners terminate, join, kill if necessary, and
  close their owned handles. RAG retains its Windows-safe subprocess policy.
- Summary queue emits one terminal outcome per task and no longer emits a
  successful task event after an error.
- Main-window close cleanup is idempotent; duplicate close events do not stop
  the recorder or cancel the queue twice.
