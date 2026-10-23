# SPEC-009: Calendar Navigation And Date-Filtered Context

Status: Implemented
Last updated: 2026-09-07

## Contract

- Calendar selection applies date and tag filters to recordings and summaries.
- Day navigation preserves the active progressive week range and emits selection
  changes for sidebar, tabs, and chat-context consumers.
- `CalendarWidget` accepts injected persistence while retaining `DBManager` as its
  compatible default.
- Daily, weekly, and pending-summary actions preserve queue-first behavior and
  retain the legacy local-worker fallback when no queue is supplied.

## Architecture And Tests

- `src/ui/calendar/layout.py` owns visual composition and
  `src/ui/calendar/summary_actions.py` owns summary-generation orchestration;
  `CalendarWidget` remains the public Qt façade.
- `tests/integration/test_calendar_selection_sync.py` verifies real SQLite filtering
  and emitted synchronization after progressive navigation, plus the selected-date
  summary request through the real queue boundary to persisted daily-summary state.

## Living implementation reference

Reviewed: 2026-10-22. Selección de fechas y sincronización de los consumidores de contexto.

- Owner: [src/ui/calendar](../../src/ui/calendar).
- Existing coverage: [tests/integration/test_calendar_selection_sync.py](../../tests/integration/test_calendar_selection_sync.py); execution results and remaining validation belong in `plan.md`.
- Request: [REQ-009](../REQUESTS.md); current feature map: [CURRENT.md](../CURRENT.md).
- Requirements and acceptance examples above describe the contract; proposed timings or resource targets require measured evidence before being treated as guarantees.
