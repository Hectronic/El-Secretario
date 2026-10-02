# Implementation Plan: Useful And Intuitive Chat Workflows

**Branch**: `036-chat-ux-workflows` | **Status**: Implemented; validated

## Delivery Outline

1. Add focused tests for the existing composer, pending/error state, source
   presentation, session search, and floating/docked state before behavior moves.
2. Extract or extend narrowly owned chat presentation-state helpers while keeping
   `ChatWidget` and conversation runtime compatibility boundaries intact.
3. Implement starter prompts, composer/draft behavior, context summary, response
   actions, source presentation, and local session search incrementally.
4. Verify cancellation/retry and floating lifecycle through real Qt signals and
   temporary SQLite, then run the full virtualenv suite.
5. Update English and Spanish documentation after user-visible behavior lands.

## UX Amendment Delivered

### Starting Point Verified Against Code

- Before this amendment, `src/ui/chat/layout.py` added an interactive
  `ContextManagerPanel` to the chat's own splitter.
  `src/ui/main_window/chat_context_sidebar.py` already added an active-chat
  section to the main right accordion, but created it with `interactive=False`;
  `sidebar_sync.py` copied state into that display panel.
- Before this amendment, `ChatWidget._show_sources()` appended expanded source
  cards to one global `source_list` below the composer. `session_applier.py`
  repeated this for loaded answers, so cards were detached from their answer.
- Before this amendment, `display_mode.py` hid the chat's context panel in floating mode;
  `ChatWidget.inspect_context()` can reveal it temporarily. This access path
  needs to remain available after the tabbed layout is simplified.

### Delivered

1. Added focused characterization and regression tests for active-chat context
   and source-to-answer behavior.
2. Made the existing right accordion's active-chat context section interactive.
   Bound it to the active chat's selection state, routed its actions to that
   chat, removed the redundant tabbed-chat panel, kept Edit separate from
   per-item removal, and retained a temporary context editor for floating chat.
3. Presented sources with their owning assistant answer in a compact disclosure,
   collapsed on creation and on session reload. Keep source navigation, missing
   provenance, and degraded retrieval states accessible.
4. Added coverage for context edits/tab switches/floating transitions and
   multiple sourced answers through real Qt signals and temporary SQLite.
   Updated English, Spanish, and Asturian chat documentation.

## Delivered

- Added multiline keyboard composer, context-aware starter prompts and selected
  context summary/removal actions, pending/error/cancel/retry/edit states,
  per-answer copy/follow-up/source controls, local session search, stable
  persistence ordering, safe rendering/loading, and floating/docked draft state.
- Added SQLite + Qt signal integration coverage for completed requests, sources,
  cancellation, and floating/docked draft preservation.
- Focused command: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest tests/ui/chat tests/ui/main_window/test_sidebar_content.py tests/ui/main_window/test_chat_floating.py tests/integration/test_chat_session_persistence.py tests/worker/test_chat_thread_cancellation.py tests/worker/test_worker.py::TestSearchAndChatThreads tests/ai_providers/test_async_chat_adapters.py -q`
- Full command: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest -q`
- Final results: focused suite **73 passed**; full suite **982 passed, 1 skipped, 11 subtests passed** (system tray is unavailable in the headless environment).
- Gemini and Ollama use cancellable asynchronous request APIs in the existing
  chat worker; legacy third-party sync-only providers remain compatible, with
  interruption limited to suppressing their eventual result.
- UX amendment focused command: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest tests/ui/chat tests/ui/main_window tests/integration/test_chat_session_persistence.py tests/worker/test_chat_thread_cancellation.py tests/worker/test_worker.py::TestSearchAndChatThreads tests/test_chat_widget_context.py tests/test_tab_context_menu.py -q` — **183 passed**.
- UX amendment full command: `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest -x --tb=short -q` — **987 passed, 1 skipped, 11 subtests passed**; the skip is the unavailable system tray in offscreen mode.

## Integration Boundary Decision

This feature crosses chat UI/signals, worker lifecycle, session persistence,
context synchronization, and floating main-window behavior. It requires real
SQLite plus Qt-signal integration coverage; provider and RAG boundaries may use
deterministic doubles.
