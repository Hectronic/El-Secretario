# Architecture Notes

This document records the current architecture and the target direction for expanding El Secretario without returning to large flat modules.

## Current Shape

El Secretario is a PyQt desktop application with local persistence, audio/STT processing, AI-assisted summarization, RAG search, and chat workflows.

Main runtime areas:

- `main.py`: application bootstrap, environment guards, Qt application setup, and `MainWindow` launch.
- `src/ui/`: PyQt widgets and UI coordinators.
- `src/ui/main_window/`: main shell and coordinators for tabs, sidebar actions, sidebar content, sidebar sync, setup actions, floating chat, and summary queue status.
  - `content_tabs.py` now owns note/chat/summary tab lifecycle and context-driven tab openers.
- `src/ui/chat/`: pure-ish chat state/rendering/context helpers used by `ChatWidget`.
- `src/ui/settings/`: settings panels grouped by product area.
- `src/ui/audio_editor/`: waveform editor and audio-editing UI.
- `src/worker_components/`: transcription worker internals, runtime/device selection, subprocess isolation, and fallback policy.
- `src/stt_providers/`: provider adapters for `faster-whisper`, `openai-whisper`, and `sherpa-onnx`.
- `src/database.py`: backwards-compatible `DBManager` facade. Aggregate-specific SQLite operations live in `src/persistence/`.
- `src/persistence/`: schema/migrations plus repositories for records, chat sessions, transcription logs, summaries, and tasks.
- `src/notebook_database.py`: notebook-specific persistence.
- `src/rag_engine.py`: Chroma-backed RAG indexing/search with Windows-safe subprocess fallbacks.
- `src/ai_provider.py`, `src/ai_assistant.py`, `src/summary_generator.py`: AI provider abstraction and summary/chat generation flows.

## Refactor Baseline

The repository has already moved several high-growth areas away from older flat modules:

- `src/ui/main_window.py` has been split into the `src/ui/main_window/` package. `MainWindow` remains in `src/ui/main_window/__init__.py`, while tab handling, floating chat, sidebar actions, sidebar content, sidebar sync, and setup actions live in focused coordinators.
- Chat-specific helpers have been extracted from `src/ui/chat_widget.py` into `src/ui/chat/`, including context building, session state, session loading/applying, rendering, theme styles, header state, busy state, and the add-context dialog.
- Settings UI has been split into `src/ui/settings/` panels for audio, general, prompts, and RAG configuration.
- The audio editor has moved from a flat widget into `src/ui/audio_editor/`, with separate widget and waveform modules.
- Legacy worker code has moved from `src/worker.py` and `src/whisper_subprocess.py` into `src/worker_components/` plus provider adapters in `src/stt_providers/`.
- Shared dialogs/components have started moving out of broad modules into targeted files such as `src/ui/filter_dialog.py`, `src/ui/speaker_dialog.py`, `src/ui/secret_field_widget.py`, and `src/ui/context_manager_panel.py`.
- Summary queue logic now lives in `src/app/summary_queue/` (tasks/completion/history/rag_reindex/workers/runtime/threads/worker_factory/worker_signals/worker_lifecycle/actions/presentation), while `src/ui/summary_task_queue.py` remains a thin Qt queue adapter for signals and worker lifecycle wiring.
- Tests now partially mirror the new feature packages under `tests/ui/main_window/`, `tests/ui/chat/`, `tests/ui/settings/`, `tests/ui/audio_editor/`, `tests/worker_components/`, and `tests/stt_providers/`.

See `docs/specs/REFACTOR-2026-05-feature-packages.md` for the behavior-preserving refactor record.

## Product Capabilities

The product currently has these major capability groups:

- Capture and import audio.
- Transcribe and diarize recordings with configurable STT backends.
- Edit recordings with safe backups and automatic retranscription.
- Organize recordings as favorites, tags/collections, notebooks, and calendar views.
- Search semantically with RAG and keyword fallback behavior.
- Chat with selected recordings, dates, notebooks, collections, and explicit context.
- Generate recording, daily, and weekly summaries.
- Extract and manage tasks from recordings and summaries.
- Export/import metadata and application data.
- Configure providers, prompts, runtime preferences, RAG behavior, theme, and secrets.

## Boundaries

Use these boundaries when adding new features:

- UI widgets own presentation, user interaction, and Qt signal wiring only.
- Coordinators own cross-widget orchestration inside a UI area, especially `MainWindow` behavior.
- Services own non-Qt business workflows and should be testable without constructing a widget.
- Provider adapters own external/runtime-specific integration details.
- Persistence classes own SQL and data shape translation, not UI decisions.
- Specs own expected product behavior and acceptance tests before implementation.

## Current Architecture Risks

- `src/ui/main_window/__init__.py` remains the main orchestration hotspot. It still mixes app composition, tab lifecycle, chat lifecycle, sidebar state, notebook actions, search, and settings. Summary queue status/UI synchronization and RAG runtime/startup summary scheduling now live in focused coordinators.
- `src/ui/main_window/bootstrap.py` now owns the deterministic startup sequence, but the remaining shell still owns a lot of application wiring.
- `src/ui/main_window/content_tabs.py` has started pulling tab-opening behavior out of the shell, but `MainWindow` still has legacy wrappers for some content actions.
- `src/database.py` is now a thin compatibility facade over `src/persistence/`; preserve this public import path while callers are migrated incrementally to aggregate-specific repositories where appropriate.
- `src/ui/recording_widget.py` is now mostly a Qt orchestration shell for recording detail and legacy audio-edit tabs. Focused recording-tab UI builders, controls, small state helpers, direct transcription flow helpers, AI action helpers, speaker mapping, audio trim helpers, and RAG indexing helpers live under `src/ui/recording/`; remaining risk is broad widget-level orchestration and persistence coupling.
- `src/ui/welcome_widget.py` mixes landing page layout, recorder configuration, microphone testing, favorites, search, today view, and settings persistence.
- `src/ui/summary_task_queue.py` still carries queue orchestration and signal wiring complexity, but most non-Qt queue logic already lives in `src/app/summary_queue/`.
- `src/rag_engine.py` combines vector store adapter, in-memory fallback, subprocess entrypoints, keyword fallback, Chroma compatibility, and Windows safety policy.
- `src/ui/styles.py` is a large shared stylesheet module. It is useful centrally, but feature-specific styling should not keep growing there by default.

## Target Direction

Prefer incremental extraction over large rewrites.

Recommended package direction:

- `src/app/`: application services and use cases that coordinate persistence, workers, RAG, and AI without depending on widgets.
- `src/domain/`: small dataclasses/value objects for records, tasks, summaries, chat contexts, transcription requests, and audio-edit plans.
- `src/persistence/`: repositories and migrations split by aggregate.
- `src/services/`: reusable workflows such as transcription orchestration, summary scheduling, task extraction, RAG indexing, export/import, and audio editing.
- `src/ui/<feature>/`: widgets plus feature-specific presenters/coordinators.
- `src/integrations/`: AI, STT, vector store, filesystem, and platform-specific adapters.

Do not move everything at once. Move code when a spec or change touches that area and tests can pin behavior first.

## Refactor Queue

Recommended next cuts:

1. Move RAG subprocess/keyword/vector-store adapter logic out of `RAGEngine` into smaller adapter modules.
2. Continue shrinking `MainWindow` by moving notebook, search, settings, collections/calendar, and the remaining content wrappers into focused coordinators.
3. Continue shrinking `RecordingWidget` by moving deletion, open-chat, playback adapters, and persistence-facing orchestration into focused modules/services; UI builders, shared controls, direct transcription flow helpers, AI action helpers, speaker mapping, audio trim helpers, and RAG indexing helpers already live under `src/ui/recording/`.
4. Move `WelcomeWidget` recorder configuration and microphone test behavior into a separate component/service.
5. Migrate selected application services to the repositories in `src/persistence/` only when doing so reduces coupling; retain `DBManager` as the compatibility boundary for existing UI code.

## Testing Expectations

- Use `./.venv/bin/python -m pytest` first, then `./venv/bin/python -m pytest`, or `./run_with_test.sh`.
- New code should have tests mirroring the source package.
- Refactors should add characterization tests before behavior-preserving moves.
- Shared UI, worker, STT, or threading changes should run focused tests and then the full suite before finishing.
- Refactors should use the `spec-driven-refactor` skill so specs and architecture notes stay current.
