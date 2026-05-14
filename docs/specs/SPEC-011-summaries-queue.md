# SPEC-011: Summaries And Background Queue

Status: Implemented
Owner: TBD
Last updated: 2026-05-14

## Problem

Users need long-running AI and transcription work to run sequentially, visibly, and safely without blocking the desktop UI. Summary generation, task extraction, transcription retries, and RAG reindexing must share a consistent queue contract.

## Scope

- In scope: recording summaries, daily summaries, weekly summaries, task extraction, queued transcription, RAG reindexing, deduplication, cancellation, progress/status updates, retry wait state, and session history.
- Out of scope: provider-specific AI prompting, STT model internals, UI rendering of queue rows, and database schema redesign.

## User Stories

- As a user, I want queued AI work to run one item at a time so that heavy jobs do not compete unpredictably.
- As a user, I want duplicate jobs skipped so that repeated clicks do not create redundant work.
- As a user, I want progress, status, and history so that I can understand what the app is doing.
- As a user, I want queued transcription to respect my configured backend/device/runtime settings.
- As a user, I want recording summaries to chain task extraction when appropriate so that action items appear automatically.

## Acceptance Criteria

- Given a recording summary is queued, when it completes, then the recording summary is persisted and task extraction is queued for that record.
- Given task extraction returns a JSON list, when it completes, then generated tasks are persisted as AI-generated tasks for the source record.
- Given task extraction is requested for a record with existing AI tasks, when force is false, then the request is skipped.
- Given a queued transcription completes outside batch processing, when text is persisted, then a recording summary is queued.
- Given a queued transcription completes from batch processing, when text is persisted, then no summary is chained automatically.
- Given a queued transcription fails with a fatal subprocess timeout or crash, when the queue handles the error, then the task is marked skipped and the next queued task starts.
- Given batch processing encounters a fatal transcription timeout or crash, when the item is reloaded or updated in the UI, then it is shown as skipped and the batch continues with later items.
- Given RAG reindexing runs, when eligible records are found, then each record's AI text is indexed with title/date/tags/type metadata.
- Given a duplicate task is queued or already running, when the same dedupe key is requested, then the duplicate request is skipped.
- Given a worker emits retry wait state, when the queue receives it, then wait state and status signals are emitted.

## Architecture Notes

- Qt adapter: `src/ui/summary_task_queue.py` owns Qt signals, `QThread` wiring, worker lifecycle, cancellation, and UI-facing queue state.
- Application helpers: `src/app/summary_queue/helpers.py` owns non-Qt helper logic for task extraction parsing and audio duration probing.
- Task factories: `src/app/summary_queue/tasks.py` owns queue task payload construction, source normalization, and dedupe key calculation.
- Queue history: `src/app/summary_queue/history.py` owns session history storage, newest-first projection, and consecutive status-trace deduplication.
- RAG reindexing: `src/app/summary_queue/rag_reindex.py` owns candidate selection, existing-index checks, metadata building, and the indexing loop.
- Runtime/thread helpers: `src/app/summary_queue/runtime.py` owns worker stop/cleanup utilities, retry-wait message shaping, and runtime stats aggregation.
- Qt thread wrappers: `src/app/summary_queue/threads.py` owns `RAGReindexThread` so `src/ui/summary_task_queue.py` stays focused on adapter orchestration.
- Completion handling: `src/app/summary_queue/completion.py` owns post-worker persistence and returns actions for the Qt adapter to apply.
- Worker config: `src/app/summary_queue/workers.py` owns transcription worker kwargs preparation from settings and queued task data.
- Worker creation: `src/app/summary_queue/worker_factory.py` owns per-task worker construction and task-type specific signal hookups.
- Worker signal wiring: `src/app/summary_queue/worker_signals.py` owns common worker signal wiring (`error`, `finished`, optional status/retry).
- Worker start lifecycle: `src/app/summary_queue/worker_lifecycle.py` owns the queue-start lifecycle for current-worker set, started events, history append, queue-state emit, and start.
- Queue widget presentation/actions: `src/app/summary_queue/presentation.py` and `src/app/summary_queue/actions.py` own UI-facing formatting/snapshots and queue action orchestration extracted from `QueueManagementWidget`.
- Persistence: `src/database.py` owns summary, transcription, and task persistence.
- Workers/integrations: `src/summary_generator.py`, `src/ai_assistant.py`, `src/worker_components/transcriber_thread.py`, and RAG engine integrations provide the actual work.
- Platform constraints: queued transcription must preserve backend, device, compute type, `force_cpu`, diarization, and CUDA cleanup policy.

## Test Plan

- Unit: helper parsing, audio-duration fallback, dedupe keys, queue history, skip behavior.
- Integration: summary-to-task chaining, queued transcription persistence, queue widget updates, RAG reindex worker.
- UI: queue management widget reflects current/pending/history state.
- Manual: run a real queued summary, task extraction, transcription, and RAG reindex on Ubuntu and Windows before release.

## Documentation

- Feature registry: `docs/specs/README.md`.
- Architecture: `docs/ARCHITECTURE.md`.

## Refactor Notes

- 2026-05-10: extracted pure helper functions from `src/ui/summary_task_queue.py` to `src/app/summary_queue/helpers.py` while preserving compatibility aliases in the Qt adapter.
- 2026-05-11: extracted queue task factories and dedupe key logic from `src/ui/summary_task_queue.py` to `src/app/summary_queue/tasks.py`.
- 2026-05-11: extracted queue session history and status-trace deduplication from `src/ui/summary_task_queue.py` to `src/app/summary_queue/history.py`.
- 2026-05-11: extracted RAG reindex candidate selection and indexing loop from `RAGReindexThread` to `src/app/summary_queue/rag_reindex.py`.
- 2026-05-11: extracted post-worker persistence and completion actions from `_on_worker_completed` to `src/app/summary_queue/completion.py`.
- 2026-05-11: extracted transcription worker kwargs preparation from `_start_next_if_idle` to `src/app/summary_queue/workers.py`.
- 2026-05-11: fatal transcription subprocess timeouts and crashes are now marked as skipped in the central queue so later tasks continue immediately.
- 2026-05-11: batch processing now renders fatal transcription errors as skipped in the UI and continues to later items.
- 2026-05-12: batch processing progress now advances on terminal success, failure, or skip so the UI reflects finished work instead of only successful completions.
- 2026-05-12: batch processing now requires the central queue; the legacy direct transcription path was removed so all heavy work goes through the unified queue.
- 2026-05-12: queue observability now includes runtime metrics (`running`, `pending`, `queued`, `finished`, `failed`, `skipped`) exposed by the queue manager and rendered in the queue management widget.
- 2026-05-13: extracted queue runtime helpers (`stop_worker`, cleanup, retry-wait state shaping, runtime stats aggregation) to `src/app/summary_queue/runtime.py`.
- 2026-05-13: moved `RAGReindexThread` from `src/ui/summary_task_queue.py` to `src/app/summary_queue/threads.py` to reduce Qt thread wiring in the UI adapter.
- 2026-05-14: extracted queue action/presentation logic from `src/ui/queue_management_widget.py` to `src/app/summary_queue/actions.py` and `src/app/summary_queue/presentation.py`, including consolidated queue snapshots.
- 2026-05-14: extracted worker creation from `SummaryTaskQueueManager._start_next_if_idle` to `src/app/summary_queue/worker_factory.py`.
- 2026-05-14: extracted common worker signal wiring from `SummaryTaskQueueManager._start_next_if_idle` to `src/app/summary_queue/worker_signals.py`.
- 2026-05-14: extracted queue worker start lifecycle from `SummaryTaskQueueManager._start_next_if_idle` to `src/app/summary_queue/worker_lifecycle.py`.

## Open Questions

- Should task payloads become dataclasses before moving more queue logic out of Qt?
- Should RAG reindexing eventually move from `src/app/summary_queue/rag_reindex.py` to a broader RAG service package if non-queue callers need it?
