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

## Integration Boundary Decision

This feature crosses chat UI/signals, worker lifecycle, session persistence,
context synchronization, and floating main-window behavior. It requires real
SQLite plus Qt-signal integration coverage; provider and RAG boundaries may use
deterministic doubles.
