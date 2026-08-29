# SPEC-008: Active Chat Context Sidebar

Status: Implemented
Owner: TBD
Last updated: 2026-06-27

## Problem

Users need the right sidebar to reflect the context of the currently active chat without duplicating or losing the chat's own context state. The sidebar must appear only when a chat is active, hide or fall back when no chat is selected, and keep tabbed and floating chat widgets synchronized with the app-wide date, week, and tag filters.

## Scope

- In scope: reusable context panel state, active chat context sidebar visibility, sidebar fallback behavior, synchronization from global date/week/tag filters into tabbed and floating chats, notebook and forced-record context mirroring, collapsed-state persistence, and context refresh when chats are opened, floated, docked, minimized, restored, closed, or deleted.
- Out of scope: chat message generation and session persistence covered by SPEC-007, RAG indexing/search internals covered by SPEC-006, calendar selection behavior covered by SPEC-009, notebook/tag management covered by SPEC-010, and database schema redesign.

## User Stories

- As a user, I want the right sidebar to show the context for the active chat so that I can verify what the assistant will use.
- As a user, I want the sidebar to disappear or fall back to another useful section when I leave chat so that non-chat workflows are not cluttered.
- As a user, I want global date, week, and tag filters to update open chats so that chat context follows my current app selection.
- As a user, I want floating chats to receive the same global context updates as tabbed chats so that floating mode behaves consistently.
- As a user, I want pinned recordings and notebook selections to survive context panel mirroring, collapse/expand, float/dock, and restore flows.

## Acceptance Criteria

- Given the active central tab is a chat widget, when the active chat context section syncs, then the right sidebar chat-context container becomes visible and restores state from the chat widget's context panel.
- Given no active chat widget is available, when the active chat context section syncs, then the chat-context container is hidden.
- Given the chat-context section is active and no chat widget is available, when sync runs, then the right sidebar falls back to the previous non-chat section or to tasks when available.
- Given a context panel has checked notebooks, forced records, current date/week, tags, sync-enabled state, and collapsed state, when its state is serialized and applied to another panel, then all of those fields are restored.
- Given `restore_from_panel(None)` is called, when no source panel exists, then no error is raised and existing state is left untouched.
- Given app-wide week/date/tag state changes, when active tabs are synced, then calendar tabs, chat tabs, task tabs, and floating chat widgets receive the same normalized filter state.
- Given the global tag filter is `All`, when active tabs are synced, then downstream widgets receive no tag filter rather than the literal `All` label.
- Given a chat context panel is collapsed, when its chat is floated, minimized, restored, or docked, then collapsed state remains consistent after sidebar sync.
- Given a chat tab or floating chat closes, when sync runs, then the active chat context sidebar no longer points at the closed widget.
- Given sidebar context restoration fails unexpectedly, when sync attempts to mirror the active chat context, then the failure is logged and the app continues running.

## Architecture Notes

- Reusable panel: `src/ui/context_manager_panel.py` owns context display, notebook check state, forced records, date/week/tag labels, sync checkbox state, collapse/expand state, serialization, application, and restoration from another panel.
- Main-window sync: `src/ui/main_window/sidebar_sync.py` owns active chat detection, right-sidebar chat-context visibility, fallback section selection, panel mirroring, and propagation of global date/week/tag filters to tabbed and floating widgets.
- Sidebar construction: `src/ui/main_window/chat_context_sidebar.py` creates and registers the `chat_context` right-sidebar section with a non-interactive `ContextManagerPanel`; `src/ui/main_window/__init__.py` remains the layout shell and delegates sync through `_sync_chat_context_section`.
- Sidebar content refresh: `src/ui/main_window/sidebar_content.py` refreshes history/tags/tasks and indirectly keeps welcome/history-driven context sources current after sidebar reloads.
- Chat widgets: `src/ui/chat_widget.py` owns the interactive context panel and exposes `update_from_global_selection` so sidebar sync can push global filters into each open chat.
- Floating chat lifecycle: `src/ui/main_window/chat_floating.py` calls sidebar sync when chats float, dock, minimize, restore, close, or update context so the right sidebar mirrors the active chat state.
- Tab lifecycle: `src/ui/main_window/tab_lifecycle.py`, `src/ui/main_window/recording_tabs.py`, and `src/ui/main_window/content_tabs.py` call sidebar sync when visible tabs or chat contexts change.
- Platform constraints: preserve PyQt parent/child ownership when mirroring state and moving chat widgets between tab and floating hosts on Ubuntu and Windows.

## Test Plan

- Unit: `ContextManagerPanel` serialize/apply/restore state, notebook check-state restoration, forced-record display, collapsed state, and no-op restore from `None`.
- Main-window sync: active chat detection, chat-context sidebar visibility, fallback behavior, panel restoration, and global filter propagation to calendar, chat, task, and floating chat widgets.
- Integration: current-tab changes, tab close, floating chat float/dock/minimize/restore, and chat context section visibility from main-window tests.
- Manual: open two chat tabs with different context, switch between them, float/dock one chat, minimize/restore floating chat, change date/week/tag filters, and verify the right sidebar mirrors the active chat only.

## Documentation

- Feature registry: `docs/specs/README.md`.
- Refactor record: `docs/specs/REFACTOR-2026-05-feature-packages.md`.
- Related specs: SPEC-007 covers chat sessions and chat-owned context assembly; SPEC-009 covers calendar navigation and date-filter selection; SPEC-010 covers notebooks and tags.

## Refactor Notes

- 2026-06-27: created the dedicated active chat context sidebar spec for `ContextManagerPanel` and `SidebarSyncCoordinator` behavior.
- 2026-06-27: recorded `src/ui/main_window/sidebar_sync.py` as the focused owner for right-sidebar chat-context synchronization while `MainWindow` remains the delegation shell.
- 2026-06-27: extracted active chat context section construction into `src/ui/main_window/chat_context_sidebar.py`.

## Open Questions

- Should the remaining right-sidebar section creation move out of `MainWindow.__init__` into dedicated builders once more section contracts are documented?
- Should context panel state use a typed dataclass shared by `ContextManagerPanel`, `ChatWidget`, and `SidebarSyncCoordinator` instead of raw dictionaries?
- Should floating chat focus/activation explicitly select the mirrored sidebar source when multiple floating chats are visible?
