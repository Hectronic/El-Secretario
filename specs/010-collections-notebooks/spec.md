# SPEC-010: Collections, Tags, And Notebooks

Status: Implemented
Owner: TBD
Last updated: 2026-09-08

## Problem

Users need durable ways to group recordings and notes beyond chronological history,
then open those groups as focused views or chat contexts.

## Scope

- In scope: recording tags/collections, notebook creation and entries, sidebar
  navigation, and opening collection/notebook views or chat contexts.
- Out of scope: recording detail editing (SPEC-004), chat session persistence
  (SPEC-007), and import/export mechanics (SPEC-014).

## User Stories

- As a user, I want to classify recordings with tags and browse a collection so
  that related work is easy to find.
- As a user, I want notebooks with text or audio entries so that longer-lived
  research can be organized separately from individual recordings.

## Acceptance Criteria

- Given a notebook is created, when text or audio entries are added, then the same
  notebook returns those entries in its persisted list.
- Given a notebook is deleted, when it has entries, then its entries are removed
  with it.
- Given a sidebar notebook or collection is selected, when it has a valid identity,
  then the matching content view opens; empty selections do not open a view.
- Given a tag is selected for chat, when chat is opened, then the tag is passed as
  explicit context rather than copied into a separate data store.

## Architecture Notes

- UI: `src/ui/collection_widget.py`, `src/ui/notebook_widget.py`, and
  `src/ui/main_window/window_navigation.py` own feature views and navigation.
  `src/ui/notebooks/entry_widget.py` owns a rendered notebook entry, while the
  widget remains the visible shell.
- Persistence: `src/notebook_database.py` owns notebook SQLite tables; recording
  tags remain in `src/persistence/records.py` behind `DBManager`.
- Integrations: `src/ui/notebooks/actions.py` owns notebook-entry persistence and
  audio-file deletion; `src/ui/notebooks/transcription_runtime.py` owns configured
  transcription worker lifecycle. `src/ui/main_window/sidebar_organization.py` owns collection and
  notebook sidebar content; `sidebar_content.py` remains its compatible façade.
  `src/ui/main_window/content_tabs.py` opens reusable views and chat contexts.
- Platform constraints: SQLite and Qt sidebar behavior are identical on Windows,
  Ubuntu, and macOS.

## Test Plan

- Unit/persistence: `tests/test_notebooks.py` covers create, entries, rename, and
  cascading deletion against SQLite.
- UI: `tests/ui/main_window/test_window_navigation.py` and
  `tests/ui/main_window/test_content_tabs.py` cover sidebar routing and tab reuse.
- Integration: `tests/integration/test_sidebar_content_persistence.py` verifies real
  recording and notebook SQLite stores populate the sidebar and produce notebook
  chat context. `tests/integration/test_notebook_widget_persistence.py` verifies a
  real notebook database receives a worker transcription result, refreshes the Qt
  entry list, and deletes associated audio safely.
- Manual: create a notebook, add text and audio entries, reopen it, and open a
  notebook/collection chat on each supported desktop platform.

## Documentation

- README: notebooks and collections are listed as organization features.
- Other docs: SPEC-007 defines chat context semantics; SPEC-014 covers notebook
  export/import.

## Refactor Notes

- 2026-09-08: moved entry rendering, entry/file actions, and notebook audio-note
  transcription lifecycle to `src/ui/notebooks/`; `NotebookWidget` retains UI,
  dialog, recording-control, and navigation ownership.
- 2026-09-09: moved notebook Qt composition and entry-detail dialog to
  `src/ui/notebooks/view.py` and `detail_dialog.py`; `NotebookWidget` now
  coordinates recording, persistence refresh, transcription, and signals only.

## Open Questions

- Should notebook persistence migrate from its dedicated SQLite file to the
  aggregate persistence package in a future explicit migration?
