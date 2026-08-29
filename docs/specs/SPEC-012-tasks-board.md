# SPEC-012: Task Board And Sidebar

Status: Implemented
Owner: TBD
Last updated: 2026-05-27

## Problem

Users need a reliable task board and sidebar that show actionable items from recordings, notes, daily context, and weekly context without depending on which tab is currently active.

## Scope

- In scope: manual tasks, AI-generated task extraction, task board filtering, task completion, sidebar task summaries, task ordering, and source navigation.
- Out of scope: AI prompt design for extraction, summary generation policy, and database schema redesign.

## User Stories

- As a user, I want to open the full Tasks tab from the sidebar so that I can review and manage all pending work.
- As a user, I want global calendar and tag filters to apply to the Tasks tab so that the board matches my current working context.
- As a user, I want to create, edit, complete, delete, and reorder tasks without losing their recording/date/week context.
- As a user, I want tasks generated from recordings or summaries to preserve source metadata so that I can trace them back.

## Acceptance Criteria

- Given the user clicks the sidebar Tasks open action, when no Tasks tab exists, then the app opens a full Tasks tab.
- Given the user clicks the sidebar new task action, when no Tasks tab exists, then the app opens Tasks and shows the create-task dialog.
- Given a Tasks tab already exists, when the user opens Tasks again, then the existing tab is focused and refreshed.
- Given a calendar week, day, or tag filter is active, when the Tasks tab opens or syncs, then those filters are applied to the board.
- Given the active date filter is represented as `QDate`, Python `date`, or an ISO string, when the Tasks tab applies filters, then it normalizes the value before querying tasks.
- Given tasks are selected, when the user completes, edits, deletes, or reorders them, then persisted task data and sidebar state are updated.

## Architecture Notes

- Main tab lifecycle: `src/ui/main_window/content_tabs.py` owns opening and reusing the full Tasks tab.
- Task board UI: `src/ui/tasks_list_widget.py` owns task listing, filters, bulk actions, create/edit dialogs, and source navigation signals.
- Sidebar actions: `src/ui/main_window/tasks_sidebar_actions.py` owns compact sidebar task refresh and context actions.
- Queue integration: `src/ui/summary_task_queue.py` and `src/app/summary_queue/` persist AI-generated tasks after extraction.
- Persistence: `src/database.py` owns task CRUD, date/week filtering, ordering, and completion state.

## Test Plan

- Unit: task board filter normalization, task CRUD callbacks, reorder persistence, and snapshot modes.
- Integration: summary queue task extraction persistence and duplicate/skip behavior.
- UI: main window content-tab coordinator opens/reuses Tasks and sidebar actions refresh compact tasks.
- Manual: open Tasks from the sidebar with no filter, day filter, week filter, and tag filter.

## Documentation

- Feature registry: `docs/specs/README.md`.

## Open Questions

- Should task board filtering move to an app-level service if more tabs need the same normalization logic?
