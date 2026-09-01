# Spec-Driven Development

This folder is the product behavior registry for El Secretario. Use it to define functionality before implementation and to keep tests tied to user-visible behavior.

## Workflow

1. Create or update a feature spec before changing behavior.
2. State the user outcome, constraints, acceptance criteria, and affected architecture areas.
3. Add or update tests that map directly to acceptance criteria.
4. Implement the smallest change that satisfies the spec.
5. Update README/docs when behavior becomes user-visible.
6. Record follow-up refactors explicitly instead of hiding them inside feature work.

## Refactor and Specs Steward Subagent

The `Refactor and Specs Steward` subagent defined in `AGENTS.md` should be activated when a change touches code that is still broad, under-refactored, or missing an explicit spec contract.

Use it when:
- A touched file is listed in a refactor record's hotspot or follow-up section.
- A behavior change cannot be mapped to a `SPEC-XXX` row in the feature registry below.
- New logic is being added to a broad module instead of the smallest owning feature package.
- A compatibility shim, migration path, duplicated helper, or deferred cleanup is introduced.

The subagent must leave the specs folder current by updating the affected spec, creating a new spec, or recording the refactor follow-up here. It should keep behavior-preserving refactors small and backed by focused tests.

## Spec Format

Use this template for new specs:

```markdown
# SPEC-XXX: Feature Name

Status: Draft | Accepted | Implemented | Deprecated
Owner: TBD
Last updated: YYYY-MM-DD

## Problem

What user or product problem is being solved?

## Scope

- In scope:
- Out of scope:

## User Stories

- As a ..., I want ..., so that ...

## Acceptance Criteria

- Given ..., when ..., then ...

## Architecture Notes

- UI:
- Services:
- Persistence:
- Workers/integrations:
- Platform constraints:

## Test Plan

- Unit:
- Integration:
- UI:
- Manual:

## Documentation

- README:
- Other docs:

## Open Questions

- ...
```

## Feature Registry

| ID | Capability | Status | Main Code Areas | Representative Tests |
| --- | --- | --- | --- | --- |
| [SPEC-001](SPEC-001-audio-capture-and-import.md) | Audio capture and import | Implemented | `src/audio.py`, `src/ui/welcome_widget.py`, `src/ui/welcome/`, `src/ui/recording_in_progress_widget.py`, `src/ui/main_window/shell_actions.py`, `src/ui/main_window/recording_tabs.py` | `tests/test_recording_flow.py`, `tests/test_welcome_daily_summary_button.py`, `tests/ui/main_window/test_recording_tabs.py`, `tests/ui/main_window/test_shell_actions.py`, `tests/test_notes.py`, `tests/ui/welcome/`, `tests/test_z_audio.py` |
| [SPEC-002](SPEC-002-transcription-runtime-and-stt-provider-selection.md) | Transcription runtime and STT provider selection | Implemented | `src/transcription_options.py`, `src/worker_components/`, `src/stt_providers/` | `tests/test_transcription_options.py`, `tests/worker/`, `tests/worker_components/`, `tests/stt_providers/` |
| SPEC-003 | Diarization and speaker management | Implemented | `src/worker_components/transcriber_thread.py`, `src/ui/speaker_dialog.py`, `src/ui/recording/speaker_actions.py`, `src/ui/recording_widget.py` | `tests/test_diarization_toggle.py`, `tests/ui/test_speaker_dialog.py`, `tests/ui/recording/test_speaker_actions.py` |
| [SPEC-004](SPEC-004-recording-metadata-notes-favorites-deletion.md) | Recording metadata, notes, favorites, deletion | Implemented | `src/database.py`, `src/persistence/records.py`, `src/ui/recording_widget.py`, `src/ui/recording/`, `src/ui/main_window/recording_tabs.py`, `src/ui/note_widget.py`, `src/ui/components.py` | `tests/test_database.py`, `tests/persistence/`, `tests/test_notes.py`, `tests/test_deletion.py`, `tests/test_recording_widget_ui.py`, `tests/ui/recording/`, `tests/ui/main_window/test_recording_tabs.py` |
| SPEC-005 | Waveform audio editor and safe retranscription | Implemented | `src/ui/audio_editor/`, `src/ui/recording/audio_trim.py`, `src/audio.py`, `src/ui/main_window/recording_tabs.py` | `tests/ui/audio_editor/`, `tests/ui/recording/test_audio_trim.py`, `tests/test_audio_editing.py`, `tests/test_recording_flow.py` |
| [SPEC-006](SPEC-006-rag-indexing-semantic-search.md) | RAG indexing and semantic search | Implemented | `src/rag_engine.py`, `src/rag/`, `src/ui/main_window/runtime_startup.py`, `src/ui/search_results_widget.py`, `src/ui/main_window/` | `tests/rag/`, `tests/test_rag_engine.py`, `tests/test_rag_fallback.py`, `tests/test_search.py`, `tests/ui/main_window/test_runtime_startup.py` |
| [SPEC-007](SPEC-007-chat-sessions-context-builder-floating-chat.md) | Chat sessions, context builder, and floating chat | Implemented | `src/ui/chat_widget.py`, `src/ui/chat/`, `src/ui/context_manager_panel.py`, `src/ui/main_window/chat_floating.py` | `tests/test_chat_widget_context.py`, `tests/ui/chat/`, `tests/ui/main_window/test_chat_floating.py` |
| [SPEC-008](SPEC-008-active-chat-context-sidebar.md) | Active chat context sidebar | Implemented | `src/ui/context_manager_panel.py`, `src/ui/main_window/sidebar_sync.py`, `src/ui/main_window/sidebar_content.py` | `tests/test_chat_context_sync.py`, `tests/ui/main_window/test_sidebar_sync.py` |
| SPEC-009 | Calendar navigation and date-filtered context | Implemented | `src/ui/calendar_widget.py`, `src/ui/main_window/sidebar_sync.py`, `src/database.py` | `tests/test_calendar_logic.py`, `tests/test_calendar_ui.py`, `tests/test_calendar_multiselection.py` |
| SPEC-010 | Collections/tags and notebooks | Implemented | `src/ui/collection_widget.py`, `src/ui/notebook_widget.py`, `src/notebook_database.py`, `src/ui/main_window/sidebar_content.py` | `tests/test_notebooks.py`, `tests/test_tasks_sidebar_calendar_sync.py` |
| SPEC-011 | Summaries: recording, daily, weekly, queueing | Implemented | `src/summary_generator.py`, `src/persistence/summaries.py`, `src/ui/summary_task_queue.py`, `src/app/summary_queue/`, `src/ui/main_window/summary_queue_status.py`, `src/ui/main_window/runtime_startup.py`, `src/ui/summary_viewer.py`, `src/ui/summary_batch_widget.py` | `tests/test_summary_generator_logic.py`, `tests/test_summary_queue.py`, `tests/test_summary_task_queue_integration.py`, `tests/ui/main_window/test_summary_queue_status.py`, `tests/ui/main_window/test_runtime_startup.py`, `tests/app/summary_queue/` |
| SPEC-012 | Task extraction and task board/sidebar | Implemented | `src/ui/tasks_list_widget.py`, `src/ui/task_batch_widget.py`, `src/ui/summary_task_queue.py`, `src/persistence/tasks.py` | `tests/test_tasks_list_widget.py`, `tests/test_pending_summary_counts.py`, `tests/test_tasks_sidebar_calendar_sync.py`, `tests/persistence/` |
| SPEC-013 | Settings, secrets, prompts, theme, RAG config | Implemented | `src/ui/settings/`, `src/ui/secret_field_widget.py`, `src/ui/styles.py` | `tests/test_settings.py`, `tests/ui/settings/`, `tests/test_theme.py` |
| SPEC-014 | Export/import and maintenance tools | Implemented | `src/data_export.py`, `src/ui/tools_widget.py`, `src/ui/maintenance_widget.py` | `tests/test_data_export.py`, `tests/test_export_transcription_logs.py`, `tests/test_maintenance.py` |

## Refactor Records

| ID | Status | Scope | Specs Affected |
| --- | --- | --- | --- |
| REFACTOR-2026-05 | Implemented | Feature-package split for main window, chat, settings, audio editor, workers, provider adapters, RAG helpers, welcome screen helpers, and mirrored tests | SPEC-001, SPEC-002, SPEC-005, SPEC-006, SPEC-007, SPEC-008, SPEC-013 |
| REFACTOR-2026-08 | Implemented | Main-window summary queue status coordinator extraction | SPEC-011 |
| REFACTOR-2026-08-RUNTIME | Implemented | Main-window RAG runtime and startup summary scheduling coordinator extraction | SPEC-006, SPEC-011 |
| REFACTOR-2026-08-RECORDING-TABS | Implemented | Main-window recording tab lifecycle consolidation | SPEC-001, SPEC-004 |
| REFACTOR-2026-08-SHELL | Implemented | Main-window shell action and sidebar-content delegation extraction | SPEC-001, SPEC-004, SPEC-011 |
| REFACTOR-2026-08-LAYOUT | Implemented | Main-window visual layout composition extraction | SPEC-001, SPEC-004, SPEC-007, SPEC-008, SPEC-009, SPEC-010, SPEC-011, SPEC-012, SPEC-013 |
| REFACTOR-2026-08-LIFECYCLE | Implemented | Main-window lifecycle and navigation extraction | SPEC-001, SPEC-007, SPEC-008, SPEC-009, SPEC-010, SPEC-011 |
| REFACTOR-2026-09-RECORD-ACTIONS | Implemented | Recording detail actions and playback extraction | SPEC-004, SPEC-005, SPEC-007 |

## Spec Granularity Rules

- One spec should describe one product capability, not one code module.
- A spec can reference several modules if the behavior crosses boundaries.
- A refactor-only change should still reference the spec whose behavior it preserves.
- If a new feature touches a hotspot listed in `docs/ARCHITECTURE.md`, include an explicit extraction decision in the spec.
- Acceptance criteria should be testable. If it cannot be tested, rewrite it as an observable behavior or mark it as a manual check.

## Definition Of Done

- Spec status is updated.
- Acceptance criteria are covered by tests or explicit manual checks.
- Refactor/spec stewardship has been applied when touched code is a hotspot or lacks a matching spec.
- Relevant README and docs are updated in all maintained language variants.
- Focused tests pass.
- Full test suite is run for shared UI, worker, STT, or threading changes.
