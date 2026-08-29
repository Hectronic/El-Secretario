# SPEC-007: Chat Sessions, Context Builder, And Floating Chat

Status: Implemented
Owner: TBD
Last updated: 2026-06-27

## Problem

Users need to ask questions over selected recordings, notes, notebooks, tags, dates, tasks, and semantic search results while keeping chat sessions reusable. Chat should work as a regular tab or as a floating, resizable panel without losing context, history, title, or sidebar synchronization.

## Scope

- In scope: chat widget message flow, context assembly, context serialization/restoration, session load/save/update, title resolution, message rendering, busy/header state, add-context dialog behavior, theme styling, floating chat host behavior, dock/undock/minimize/restore/close lifecycle, and chat session sidebar actions.
- Out of scope: AI provider implementation details, RAG indexing internals, active global context sidebar behavior covered by SPEC-008, database schema redesign, and prompt-management settings covered by SPEC-013.

## User Stories

- As a user, I want to start a chat with selected recordings, tags, dates, notebooks, or a week so that answers are grounded in the current work context.
- As a user, I want chat sessions saved with their messages and context so that I can reopen them later.
- As a user, I want a chat to be docked in a tab or floating above the workspace so that I can keep asking questions while navigating other views.
- As a user, I want the context panel to show and restore the active chat context so that I understand what will be sent to the assistant.
- As a user, I want chat rendering and theme changes to stay readable in light and dark modes.

## Acceptance Criteria

- Given a chat starts with recording contexts, when the user sends a message, then the context sent to the chat worker includes composed transcription and notes for those recordings.
- Given a week/date/tag context is active, when context text is built, then matching records and tasks are included without duplicating forced recording IDs.
- Given notebook context is selected, when context text is built, then notebook entries are included with their titles and content.
- Given no date or tag filter restricts the query, when context text is built, then RAG search results are included as relevant fragments.
- Given RAG search fails while building context, when the message is sent, then the failure is logged and chat context building continues from other available sources.
- Given active date range, tag, notebook, and forced-record contexts, when a session is saved, then those contexts are serialized into the session payload.
- Given a saved session has message and context JSON, when it is loaded, then chat history, title, session ID, and context state are restored.
- Given stored session JSON is malformed, when a session is loaded, then the widget falls back to empty messages or no contexts rather than crashing.
- Given a new chat has a first user message, when the session is saved or titled, then the visible/session name is derived from that first message and truncated when needed.
- Given no session name or messages exist, when a title is resolved, then selected recording labels, tags, or date context are used before falling back to `New Chat`.
- Given the user adds manual context from the add-context dialog, when accepted, then the selected context is applied to the active context panel.
- Given the theme changes, when the chat widget receives the update, then display, input, title, and rendered markdown styles remain readable.
- Given a chat widget is floated, when it leaves the tab area, then it is wrapped in a floating host, its display mode changes to floating, and the main chat context sidebar syncs accordingly.
- Given a floating chat is docked back to a tab, when docking completes, then the chat widget returns to tab mode and its context panel is visible again.
- Given a floating chat is minimized or restored, when the action is triggered, then host state and chat widget minimized state stay in sync.
- Given a chat session is deleted from the sidebar, when the session is open in a tab or floating host, then the associated UI is closed and context sidebar state is refreshed.

## Architecture Notes

- Chat shell: `src/ui/chat_widget.py` owns the visible chat widget, user input, worker signal wiring, public chat signals, context panel composition, session lifecycle calls, and high-level UI orchestration.
- Context building: `src/ui/chat/context_builder.py` owns chat context text assembly from notebooks, forced records, date/week filters, tags, tasks, and RAG fragments, plus context serialization for sessions.
- Context parsing: `src/ui/chat/context_state.py` normalizes stored context JSON into UI-ready date, tag, notebook, and forced-record state.
- Sessions: `src/ui/chat/session_state.py`, `src/ui/chat/session_loader.py`, and `src/ui/chat/session_applier.py` own session naming, save/update payloads, malformed JSON handling, and applying loaded messages/contexts to a widget.
- Rendering/state helpers: `src/ui/chat/message_renderer.py`, `src/ui/chat/theme_styles.py`, `src/ui/chat/header_state.py`, and `src/ui/chat/busy_state.py` own markdown rendering, light/dark styles, title/header state, and input/busy controls.
- Add-context dialog: `src/ui/chat/add_context_dialog.py` owns manual context selection UI and selected-context payloads.
- Context sidebar component: `src/ui/context_manager_panel.py` is shared by chat widgets and the main window to show active context, forced records, notebooks, tags, and date filters.
- Main-window floating lifecycle: `src/ui/main_window/chat_floating.py` owns `FloatingChatHost` sizing/resizing and `FloatingChatCoordinator` dock/undock/minimize/restore/close behavior.
- Main-window session sidebar: `src/ui/main_window/chat_sessions_actions.py` owns sidebar open, open-floating, delete, and cleanup behavior for saved chat sessions.
- Content tabs: `src/ui/main_window/content_tabs.py` creates/reuses chat tabs and passes session/context parameters from other app areas.
- Platform constraints: preserve PyQt behavior on Ubuntu and Windows, including stable parent/child ownership when moving widgets between tabs and floating hosts.

## Test Plan

- Unit: context text assembly, context serialization/parsing, session naming/payload persistence, loaded-session application, message rendering, theme styles, header state, and busy state.
- Dialog/UI: add-context dialog selection and context manager panel state round trips.
- Main-window UI: floating chat host resizing, float/dock/minimize/restore/close lifecycle, chat sidebar open/open-floating/delete actions, and content-tab chat reuse.
- Integration: `ChatWidget` sends messages with recording/week/tag/task context, persists sessions, restores loaded sessions, and updates styles on theme changes.
- Manual: start chats from recording, calendar/week, tag, notebook, and search flows; float/dock/minimize/restore; delete an open session; verify light/dark readability.

## Documentation

- Feature registry: `docs/specs/README.md`.
- Refactor record: `docs/specs/REFACTOR-2026-05-feature-packages.md`.
- Related specs: SPEC-006 covers RAG indexing/search internals; SPEC-008 covers the active chat context sidebar; SPEC-013 covers prompt/provider settings.

## Refactor Notes

- 2026-06-27: created the dedicated chat spec for the existing `src/ui/chat/` helper split and main-window floating/session coordinators.
- 2026-06-27: recorded `src/ui/chat_widget.py` as the chat shell and `src/ui/main_window/chat_floating.py` plus `chat_sessions_actions.py` as the main-window ownership boundary for floating and sidebar session behavior.

## Open Questions

- Should remaining `ChatWidget` worker orchestration be split from the widget shell after provider/prompt contracts are documented in SPEC-013?
- Should floating chat layout preferences persist per session or globally once product behavior is explicitly desired?
- Should chat context assembly receive a typed context object instead of reading directly from `ContextManagerPanel` before expanding context types further?
