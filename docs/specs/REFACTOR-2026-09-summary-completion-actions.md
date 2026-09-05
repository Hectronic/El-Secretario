# REFACTOR-2026-09-SUMMARY-COMPLETION: Queue Completion And State

Status: Implemented
Last updated: 2026-09-05

## Behavior Contract

- Preserve completion follow-ups, deduplication, pending ordering, and active-task
  transitions for queued transcription and summaries.
- Preserve automatic task extraction after a completed recording summary only when
  persisted AI text is available.
- Keep `SummaryTaskQueueManager` as the owner of Qt signals and worker lifecycle.

## Moved Boundary

- From: completion-action dispatch in `src/ui/summary_task_queue.py`.
- To: `src/app/summary_queue/completion_actions.py` and
  `src/app/summary_queue/state.py`.

## Tests

- Focused: `tests/app/summary_queue/test_completion_actions.py`,
  `tests/app/summary_queue/test_state.py`,
  `tests/app/summary_queue/test_completion.py`, `tests/test_summary_queue.py`, and
  `tests/test_summary_task_queue_integration.py`.
- Full suite: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./venv/bin/python -m pytest -q`.
