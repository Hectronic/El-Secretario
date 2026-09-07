# REFACTOR-2026-05: Feature Package Split

Status: Implemented
Last updated: 2026-05-14

## Goal

Reduce large flat modules and create expansion points for future product work without changing user-facing behavior.

## Behavior Contract

- Preserved: application startup, recording/import flows, transcription runtime preferences, chat sessions, floating chat, active chat context sidebar, settings, audio editing, RAG/search, summaries, tasks, notebooks, collections, and export/import.
- Changed: source layout, ownership boundaries, and test locations.
- Out of scope: intentional product behavior changes, database schema redesign, provider changes, and UI redesign.

## Moved Boundaries

- From `src/ui/main_window.py` to `src/ui/main_window/`: main window shell plus coordinators for recording tabs, floating chat, sidebar sync, sidebar content, sidebar actions, and setup actions.
- From broad chat widget logic to `src/ui/chat/`: context builder, context state, session state, session loader/applier, message rendering, theme styles, header state, busy state, and add-context dialog.
- From flat settings code to `src/ui/settings/`: audio, general, prompts, RAG, default prompt values, and settings widget composition.
- From `src/ui/audio_editor_widget.py` to `src/ui/audio_editor/`: audio editor widget, audio chunk model, and waveform widget.
- From `src/worker.py` and `src/whisper_subprocess.py` to `src/worker_components/`: device selection, runtime policy, subprocess runner, transcription flow, transcriber thread, Sherpa helpers, and settings helpers.
- From monolithic STT handling to `src/stt_providers/`: dispatcher and provider-specific adapters for `faster-whisper`, `openai-whisper`, and `sherpa-onnx`.
- From broad dialog/component files to targeted modules: `src/ui/filter_dialog.py`, `src/ui/speaker_dialog.py`, `src/ui/secret_field_widget.py`, and `src/ui/context_manager_panel.py`.
- From repeated recording-tab button setup in `src/ui/recording_widget.py` to `src/ui/recording/controls.py`: recording action button factories, semantic style wrappers, shared playback-control creation, and media-button creation.
- From inline recording-tab panel construction in `src/ui/recording_widget.py` to focused builders in `src/ui/recording/`: transcription controls, metadata panel, content tabs, and bottom actions bar now have separate modules and direct tests.
- From small non-visual helpers in `RecordingWidget` to `src/ui/recording/state.py`: audio path resolution, AI-text presence checks, fallback record titles, and settings booleans.
- From RAG auto-index side effects in `RecordingWidget` to `src/ui/recording/rag_indexing.py`: auto-index settings checks, post-transcription record AI-text indexing, save-time composed-text indexing, metadata assembly, and skipped-status emission.
- From direct transcription startup/result persistence in `RecordingWidget` to `src/ui/recording/transcription_flow.py`: settings-to-worker config, Sherpa preflight, audio-duration probing, `TranscriberThread` creation/wiring, queue traces, and direct result persistence.
- From remaining recording-tab workflows in `RecordingWidget` to focused helpers under `src/ui/recording/`: `ai_actions.py` handles queue/legacy AI actions, `speaker_actions.py` handles speaker-label discovery/mapping, and `audio_trim.py` handles legacy trim validation, playhead math, backup creation, and in-place trim dispatch.
- From mixed record loading inside `RecordingWidget.load_record` to private owner methods: audio-editor loading, full-detail loading, audio-path resolution, and audio-source setup are now separated while preserving the public `load_record(record_id)` API.
- From `MainWindow.__init__` startup wiring to `src/ui/main_window/bootstrap.py`: deterministic startup sequence for settings snapshot, sidebar loads, task queue wiring, and the welcome screen.
- From note/chat/summary tab opening code in `src/ui/main_window/__init__.py` to `src/ui/main_window/content_tabs.py`: content tab lifecycle, session reuse, and summary duplicate detection.
- From tools/tasks/collections/calendar tab opening code in `src/ui/main_window/__init__.py` to `src/ui/main_window/content_tabs.py`: reusable content-tab orchestration with preserved filters, selection sync, and duplicate-tab reuse behavior.
- From tab close/context menu behavior in `src/ui/main_window/__init__.py` to `src/ui/main_window/tab_lifecycle.py`: tab closing policy, unsaved-recording guard, and close-all/close-others orchestration.
- From history/tags context menus in `src/ui/main_window/__init__.py` to `src/ui/main_window/sidebar_actions.py`: sidebar action routing for history entries (`recording`, `note`, `summary`) and tag actions (`Open`, `Chat`).
- From tasks sidebar rendering and actions in `src/ui/main_window/sidebar_actions.py` to `src/ui/main_window/tasks_sidebar_actions.py`: task list hydration, completion toggles, and task context-menu actions.
- From chat sessions sidebar actions in `src/ui/main_window/sidebar_actions.py` to `src/ui/main_window/chat_sessions_actions.py`: session click/open, floating open, and delete flow including open-tab/floating cleanup.
- From calendar sidebar actions in `src/ui/main_window/sidebar_actions.py` to `src/ui/main_window/calendar_sidebar_actions.py`: date/week navigation, sidebar sync trigger, and calendar highlight rendering.
- From history/tags sidebar context menus in `src/ui/main_window/sidebar_actions.py` to `src/ui/main_window/history_tags_actions.py`: history record/note/summary opening actions and tags `Open/Chat` routing.
- From welcome search flow in `src/ui/main_window/__init__.py` to `src/ui/main_window/search_actions.py`: RAG search trigger, search result tab opening, and error handling.
- From Week Details selection sync in `src/ui/main_window/__init__.py` to `src/ui/main_window/selection_sync_actions.py`: sidebar calendar/date/tag synchronization and dependent sidebar refresh.
- From history click navigation in `src/ui/main_window/__init__.py` to `src/ui/main_window/history_navigation_actions.py`: routing history row clicks to recording/note/summary tabs.
- From summary regeneration flow in `src/ui/main_window/__init__.py` to `src/ui/main_window/summary_actions.py`: payload normalization and daily summary enqueue from summary views.
- From runtime-heavy queue helpers in `src/ui/summary_task_queue.py` to `src/app/summary_queue/`: worker stop/cleanup/retry-wait runtime helpers and RAG reindex thread now live in app-level modules (`runtime.py`, `threads.py`) while UI keeps signal orchestration.
- From mixed RAG engine helpers in `src/rag_engine.py` to `src/rag/`: in-memory fallback storage, result parsing/ranking, filter composition, Chroma store initialization/compatibility, and subprocess task handling now live in focused modules while `RAGEngine` remains the public facade.
- From repeated welcome-screen button construction in `src/ui/welcome_widget.py` to `src/ui/welcome/button_factory.py`: big, round, and squircle button constructors now live in a focused helper while `WelcomeWidget` keeps the same public methods and signals.
- From welcome-screen capture, microphone test, and landing-list data state in `src/ui/welcome_widget.py` to `src/ui/welcome/`: `capture_state.py` owns saved capture settings and config mapping, `mic_test.py` owns stream lifecycle, RMS, and VU state, and `landing_data.py` owns search/favorites/today list formatting.
- From active chat context sidebar construction in `src/ui/main_window/__init__.py` to `src/ui/main_window/chat_context_sidebar.py`: the helper creates and registers the non-interactive mirrored context panel while `SidebarSyncCoordinator` keeps synchronization behavior.
- From queue-management widget logic in `src/ui/queue_management_widget.py` to `src/app/summary_queue/`: action orchestration (`actions.py`) and presentation/snapshot mapping (`presentation.py`) now live in app-level modules while the widget primarily applies mapped view state.
- From worker startup internals in `src/ui/summary_task_queue.py` to `src/app/summary_queue/`: worker construction (`worker_factory.py`), common signal wiring (`worker_signals.py`), and queue-start lifecycle (`worker_lifecycle.py`) now live in focused modules.
- From the global theme application facade in `src/ui/styles.py` to `src/ui/theme_styles.py`: static dark, light, and SNES sheets plus compatibility style constants now live in a dedicated theme resource module.
- From the monolithic `src/database.py` to `src/persistence/`: schema/migrations, records/imports, chat sessions/imports, transcription logs, summaries, and tasks now have aggregate-specific repository modules. `DBManager` remains the public compatibility facade so existing callers retain their API.
- From `CalendarWidget` summary-generation handlers to `src/ui/calendar/summary_actions.py`: daily, weekly, pending, completion, and error actions now have a focused owner while the widget retains its public Qt slots.
- From direct `DBManager` construction in `RecordingWidget` to an injected persistence port: recording detail actions and loading now share caller-provided persistence when supplied, while retaining the compatible default facade.
- From direct `DBManager` construction in `SummaryTaskQueueManager` to an injected persistence port: queued daily-summary workers now receive the same persistence boundary as the caller, preserving the compatible default facade.
- From worker-signal outcome handlers in `SummaryTaskQueueManager` to `src/app/summary_queue/execution.py`: worker completion, failure/skip policy, status traces, retry waits, cleanup, and sequential continuation now have an app-level owner.
- From inline RAG platform guards in `src/rag_engine.py` to `src/rag/runtime_policy.py`: Windows-safe delete and subprocess modes are resolved in a pure policy while macOS and Ubuntu retain in-process Chroma behavior.

## Specs Affected

- SPEC-002: transcription runtime and STT provider selection now map to `src/worker_components/` and `src/stt_providers/`.
- SPEC-005: waveform audio editor now maps to `src/ui/audio_editor/`.
- SPEC-006: RAG indexing and semantic search now maps to `src/rag_engine.py` and `src/rag/`.
- SPEC-001: audio capture and import now maps to `src/ui/welcome_widget.py`, `src/ui/welcome/`, `src/audio.py`, and `src/ui/main_window/`.
- SPEC-007: chat sessions/context/floating chat now map to `src/ui/chat/`, `src/ui/chat_widget.py`, and `src/ui/main_window/chat_floating.py`.
- SPEC-008: active chat context sidebar now maps to `src/ui/context_manager_panel.py`, `src/ui/main_window/sidebar_sync.py`, and `src/ui/main_window/sidebar_content.py`.
- SPEC-013: settings panels now map to `src/ui/settings/`.
- SPEC-009: calendar visual composition and summary actions now map to `src/ui/calendar/` while `CalendarWidget` remains the public façade.

## Tests

- Focused tests have been moved or added under `tests/ui/main_window/`, `tests/ui/chat/`, `tests/ui/settings/`, `tests/ui/audio_editor/`, `tests/rag/`, `tests/worker_components/`, and `tests/stt_providers/`.
- MainWindow coordinator extraction now includes direct unit tests for focused coordinators:
  - `tests/ui/main_window/test_tab_lifecycle.py`
  - `tests/ui/main_window/test_tasks_sidebar_actions.py`
  - `tests/ui/main_window/test_chat_sessions_actions.py`
  - `tests/ui/main_window/test_calendar_sidebar_actions.py`
  - `tests/ui/main_window/test_history_tags_actions.py`
  - `tests/ui/main_window/test_search_actions.py`
  - `tests/ui/main_window/test_selection_sync_actions.py`
  - `tests/ui/main_window/test_history_navigation_actions.py`
  - `tests/ui/main_window/test_summary_actions.py`
- Representative root-level integration tests still cover cross-feature behavior such as recording flow, chat context sync, settings, summary queue, and Windows bootstrap scripts.
- `tests/integration/test_calendar_selection_sync.py` covers real SQLite date/tag filtering, sidebar synchronization, and daily-summary queue admission.
- Recording deletion and calendar-to-queue daily-summary completion are covered with real SQLite in `tests/integration/`, while external dialogs, AI providers, and workers remain controlled test boundaries.
- Full suite status for this refactor was validated after the code change.

## Remaining Hotspots

No structural hotspots are currently confirmed. `MainWindow`,
`SummaryTaskQueueManager`, `RAGEngine`, and `DBManager` are intentional public
facades; future work should preserve their compatible APIs while extending the
smallest owning feature package or aggregate repository.

## Follow-Ups

- Use the `spec-driven-refactor` skill for future refactors so specs and architecture docs stay aligned.
- Reassess façade boundaries only when a concrete behavior cannot be assigned to an
  existing feature package or aggregate repository.
- Prefer moving behavior only after focused tests pin current contracts.
