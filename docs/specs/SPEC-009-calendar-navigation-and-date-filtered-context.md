# SPEC-009: Calendar Navigation And Date-Filtered Context

Status: Implemented
Last updated: 2026-09-06

## Contract

- Calendar selection applies date and tag filters to recordings and summaries.
- Day navigation preserves the active progressive week range and emits selection
  changes for sidebar, tabs, and chat-context consumers.
- `CalendarWidget` accepts injected persistence while retaining `DBManager` as its
  compatible default.

## Architecture And Tests

- `src/ui/calendar/layout.py` owns visual composition; `CalendarWidget` owns the
  public Qt façade and selection/summary orchestration.
- `tests/integration/test_calendar_selection_sync.py` verifies real SQLite filtering
  and emitted synchronization after progressive navigation.
