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
| SPEC-001 | Audio capture and import | Implemented | `src/audio.py`, `src/ui/welcome_widget.py`, `src/ui/recording_in_progress_widget.py`, `src/ui/main_window/` | `tests/test_recording_flow.py`, `tests/test_z_audio.py` |
| SPEC-002 | Transcription runtime and STT provider selection | Implemented | `src/transcription_options.py`, `src/worker_components/`, `src/stt_providers/` | `tests/test_transcription_options.py`, `tests/worker/`, `tests/worker_components/`, `tests/stt_providers/` |
| SPEC-003 | Diarization and speaker management | Implemented | `src/worker_components/transcriber_thread.py`, `src/ui/speaker_dialog.py`, `src/ui/recording_widget.py` | `tests/test_diarization_toggle.py`, `tests/ui/test_speaker_dialog.py` |
| SPEC-004 | Recording metadata, notes, favorites, deletion | Implemented | `src/database.py`, `src/ui/recording_widget.py`, `src/ui/note_widget.py`, `src/ui/components.py` | `tests/test_database.py`, `tests/test_notes.py`, `tests/test_deletion.py`, `tests/test_recording_widget_ui.py` |
| SPEC-005 | Waveform audio editor and safe retranscription | Implemented | `src/ui/audio_editor/`, `src/audio.py`, `src/ui/main_window/recording_tabs.py` | `tests/ui/audio_editor/`, `tests/test_audio_editing.py`, `tests/test_recording_flow.py` |
| SPEC-006 | RAG indexing and semantic search | Implemented | `src/rag_engine.py`, `src/ui/search_results_widget.py`, `src/ui/main_window/` | `tests/test_rag_engine.py`, `tests/test_rag_fallback.py`, `tests/test_search.py` |
| SPEC-007 | Chat sessions, context builder, and floating chat | Implemented | `src/ui/chat_widget.py`, `src/ui/chat/`, `src/ui/context_manager_panel.py`, `src/ui/main_window/chat_floating.py` | `tests/test_chat_widget_context.py`, `tests/ui/chat/`, `tests/ui/main_window/test_chat_floating.py` |
| SPEC-008 | Active chat context sidebar | Implemented | `src/ui/context_manager_panel.py`, `src/ui/main_window/sidebar_sync.py`, `src/ui/main_window/sidebar_content.py` | `tests/test_chat_context_sync.py`, `tests/ui/main_window/test_sidebar_sync.py` |
| SPEC-009 | Calendar navigation and date-filtered context | Implemented | `src/ui/calendar_widget.py`, `src/ui/main_window/sidebar_sync.py`, `src/database.py` | `tests/test_calendar_logic.py`, `tests/test_calendar_ui.py`, `tests/test_calendar_multiselection.py` |
| SPEC-010 | Collections/tags and notebooks | Implemented | `src/ui/collection_widget.py`, `src/ui/notebook_widget.py`, `src/notebook_database.py`, `src/ui/main_window/sidebar_content.py` | `tests/test_notebooks.py`, `tests/test_tasks_sidebar_calendar_sync.py` |
| SPEC-011 | Summaries: recording, daily, weekly, queueing | Implemented | `src/summary_generator.py`, `src/ui/summary_task_queue.py`, `src/app/summary_queue/`, `src/ui/summary_viewer.py`, `src/ui/summary_batch_widget.py` | `tests/test_summary_generator_logic.py`, `tests/test_summary_queue.py`, `tests/test_summary_task_queue_integration.py`, `tests/app/summary_queue/` |
| SPEC-012 | Task extraction and task board/sidebar | Implemented | `src/ui/tasks_list_widget.py`, `src/ui/task_batch_widget.py`, `src/ui/summary_task_queue.py`, `src/database.py` | `tests/test_tasks_list_widget.py`, `tests/test_pending_summary_counts.py`, `tests/test_tasks_sidebar_calendar_sync.py` |
| SPEC-013 | Settings, secrets, prompts, theme, RAG config | Implemented | `src/ui/settings/`, `src/ui/secret_field_widget.py`, `src/ui/styles.py` | `tests/test_settings.py`, `tests/ui/settings/`, `tests/test_theme.py` |
| SPEC-014 | Export/import and maintenance tools | Implemented | `src/data_export.py`, `src/ui/tools_widget.py`, `src/ui/maintenance_widget.py` | `tests/test_data_export.py`, `tests/test_export_transcription_logs.py`, `tests/test_maintenance.py` |

## Refactor Records

| ID | Status | Scope | Specs Affected |
| --- | --- | --- | --- |
| REFACTOR-2026-05 | Implemented | Feature-package split for main window, chat, settings, audio editor, workers, provider adapters, and mirrored tests | SPEC-002, SPEC-005, SPEC-007, SPEC-008, SPEC-013 |

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
