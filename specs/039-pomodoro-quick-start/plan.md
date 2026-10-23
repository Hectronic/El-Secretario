# Implementation Plan: Simple Pomodoro And Unified Activity Discovery

**Branch**: `039-pomodoro-quick-start` | **Status**: Implemented and validated

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

## Implementation and Validation Record

- Welcome quick-start delegates to the shared Pomodoro and break services;
  timer setup/capture controls are grouped under a collapsed secondary section.
- The existing activity timeline composes stable references to daily and weekly
  summaries with meetings, Pomodoros, and notes. Local search recognizes these
  sources plus existing recording/note content, and chat context can explicitly
  select a Pomodoro and its saved notes.

## Review on 2026-10-22

Environment: Linux, project `.venv`, Qt `offscreen`.

- Corrected selected Pomodoro tags overwriting the chat's record/task filters. The regression uses a real context panel and temporary SQLite with differently tagged notes.
- Corrected secondary controls remaining visible in an unchecked QGroupBox; its content now actually hides and reappears on expansion.
- Welcome refresh uses the coordinator's existing timer; no additional QTimer owns or polls its state. Running/paused state is visible in the localized action.
- No files moved. Owners remain productivity persistence, the Pomodoro widget, Welcome presentation and chat context packages.
- Follow-up: profile mixed-source timeline pagination on large histories before changing its read model. Native visual checks on Windows/macOS are not covered by this Linux offscreen run.

Focused unit command (120 passed):

```bash
QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest tests/ui/welcome tests/ui/chat tests/ui/context_manager tests/ui/main_window/test_search_actions.py tests/ui/test_search_results_widget.py tests/persistence tests/app/pomodoro -q
```

Focused integration command (28 passed):

```bash
QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest tests/integration/test_pomodoro_main_window.py tests/integration/test_pomodoro_timeline_flow.py tests/integration/test_chat_session_persistence.py tests/integration/test_context_manager_panel_sync.py -q
```

Integration contracts: `test_pomodoro_main_window.py` covers Welcome intent, shared service/SQLite persistence, duplicate prevention, paused/break routing and summary navigation. `test_pomodoro_timeline_flow.py` covers mixed-source chronology, note persistence, discovery and selected chat context, including preservation of tag filters. These use real Qt and SQLite; external provider/audio edges are replaced deterministically.

Full suite command (1031 passed, 1 skipped because system tray is unavailable, 11 subtests passed; 138.17 seconds):

```bash
QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest -q
```

Published branch: `039-pomodoro-quick-start`. Review: [PR #67](https://github.com/Hectronic/El-Secretario/pull/67).
