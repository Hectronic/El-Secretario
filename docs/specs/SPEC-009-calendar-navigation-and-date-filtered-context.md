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
  and emitted synchronization after progressive navigation.
