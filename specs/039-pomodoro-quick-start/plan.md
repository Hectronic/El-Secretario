# Implementation Plan: Simple Pomodoro And Unified Activity Discovery

**Branch**: `039-pomodoro-quick-start` | **Status**: Proposed

## Delivery Outline

1. Add characterization tests for the shared activity timeline, general search,
   chat context, Welcome action routing, and current Pomodoro screen.
2. Simplify the timer view around remaining time and essential focus controls;
   place metadata, break, and note tools in secondary sections.
3. Add one-click Welcome start and active-timer navigation using the existing
   coordinator, `PomodoroService`, and configured duration.
4. Extend the general chronological timeline to project Pomodoros, meetings,
   daily/weekly summaries, and other activity without making a Pomodoro-only
   feed or duplicating source records.
5. Extend general search and chat context to find and explicitly select
   Pomodoros and associated note content, retaining existing provider/RAG policy.
6. Add real Qt signal + temporary SQLite integration coverage for one-click
   start, the shared chronology, search/context discovery, and source navigation.
7. Update README, README_ES, and README_AST and run focused plus full suites.

## Integration Boundary Decision

This feature crosses Welcome UI/signals, MainWindow navigation, the shared
Pomodoro service, and SQLite persistence. Integration coverage must use real Qt
signals and a temporary SQLite database; only the clock and notification edge
may be deterministic doubles.

## Constraints

- Do not duplicate timer state or change SPEC-034's state, recovery, persistence,
  break, note, or timeline contracts.
- Quick start may set a default title through the existing widget/service path,
  but must not bypass the service's title validation or create a parallel timer.
- The single activity timeline is the only chronological activity surface.
  Pomodoro, meeting, and summary views may link into it but must not create
  feature-specific timelines.
- Search and chat context must resolve source identities to their owning records;
  index/read-model entries must not become duplicate editable source content.
