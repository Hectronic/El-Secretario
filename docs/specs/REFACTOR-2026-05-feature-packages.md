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

## Specs Affected

- SPEC-002: transcription runtime and STT provider selection now map to `src/worker_components/` and `src/stt_providers/`.
- SPEC-005: waveform audio editor now maps to `src/ui/audio_editor/`.
- SPEC-006: RAG indexing and semantic search now maps to `src/rag_engine.py` and `src/rag/`.
- SPEC-001: audio capture and import now maps to `src/ui/welcome_widget.py`, `src/ui/welcome/`, `src/audio.py`, and `src/ui/main_window/`.
- SPEC-007: chat sessions/context/floating chat now map to `src/ui/chat/`, `src/ui/chat_widget.py`, and `src/ui/main_window/chat_floating.py`.
- SPEC-008: active chat context sidebar now maps to `src/ui/context_manager_panel.py`, `src/ui/main_window/sidebar_sync.py`, and `src/ui/main_window/sidebar_content.py`.
- SPEC-013: settings panels now map to `src/ui/settings/`.

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
- Full suite status for this refactor was validated after the code change.

## Remaining Hotspots

- `src/ui/main_window/__init__.py` remains a large shell and should keep shrinking through coordinators and focused right-sidebar builders.
- `src/ui/main_window/bootstrap.py` now isolates the startup sequence, but the shell still owns tab lifecycle and broad app orchestration.
- `src/ui/main_window/content_tabs.py` now owns note/chat/summary/tools/tasks/collections/calendar tab lifecycle; remaining `MainWindow` shell reduction should focus on cross-feature orchestration and legacy wrappers.
- `src/ui/main_window/sidebar_actions.py` is now mostly an orchestrator over `tasks_sidebar_actions.py`, `chat_sessions_actions.py`, `calendar_sidebar_actions.py`, and `history_tags_actions.py`; future cuts should target direct wiring from `MainWindow` to those focused coordinators where practical.
- `src/database.py` remains a broad persistence gateway and should be split by aggregate once contract tests are explicit.
- `src/ui/recording_widget.py` is now mostly a Qt orchestration shell for the recording detail/audio-edit tab. UI panel construction, controls, state helpers, RAG indexing, record loading, direct transcription flow, AI actions, speaker mapping, and legacy trim helpers have been extracted under `src/ui/recording/`; remaining reductions should target deletion/open-chat/playback adapters and any broad persistence coupling.
- `src/ui/welcome_widget.py` still mixes landing layout, recorder configuration, microphone tests, favorites, today view, search, and settings persistence.
- `src/ui/summary_task_queue.py` now acts mostly as a Qt adapter; keep moving any remaining business-only helpers into `src/app/summary_queue/`.
- `src/rag_engine.py` now owns the public RAG facade and Windows runtime-mode selection; fallback store, Chroma initialization/compatibility, result parsing/ranking, filter composition, and subprocess task handling have moved to `src/rag/`.
- `src/ui/welcome_widget.py` still mixes landing layout and navigation signals; `src/ui/welcome/` now owns shared button constructors, capture-setting helpers, microphone-test helpers, and landing-list data formatting.

## Follow-Ups

- Use the `spec-driven-refactor` skill for future refactors so specs and architecture docs stay aligned.
- Add individual spec files for the highest-change capabilities before the next major feature: transcription runtime, chat context, summary queue, and settings.
- Prefer moving behavior only after focused tests pin current contracts.
