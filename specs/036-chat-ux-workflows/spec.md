# SPEC-036: Useful And Intuitive Chat Workflows

Status: Implemented; validated
Owner: Chat user experience
Last updated: 2026-09-28

## Problem

The chat already persists sessions and composes context, but users can still be
uncertain about what to ask, what content will be used, whether a response is in
progress, and how to act on a useful answer. The chat needs a calmer, more
discoverable workflow that makes context, response state, evidence, and common
follow-up actions explicit. In tab mode, a second context panel sits beside the
existing right sidebar. The sidebar's active-context section is read-only, while
answer sources accumulate in a separate block below the composer. These layouts
take space from reading and make context and evidence harder to use.

## Scope

- In scope: chat landing/empty states, composer ergonomics, visible context
  summary, source/evidence presentation, response actions, retry/cancel behavior,
  conversation navigation/search, accessibility, and responsive feedback.
- Out of scope: changing AI providers or prompts, changing retrieval/indexing
  policy, introducing autonomous agents, external collaboration, or replacing
  session persistence/context serialization contracts.

## User Stories

### US1 - Know how to begin

As a user, I see useful, context-aware starter actions in a new or empty chat,
so I can ask focused questions without having to infer the app’s capabilities.

### US2 - Trust the answer

As a user, I can inspect the context and sources used for an answer, so I can
judge whether the answer is grounded and navigate back to the underlying work.

### US3 - Continue efficiently

As a user, I can edit/send multiline messages naturally, cancel or retry a
request, copy useful answers, and find prior conversations, so chat feels fast
and predictable rather than opaque.

### US4 - Manage context in one sidebar

As a user, I can manage chat context from the existing right-hand sidebar,
without a second competing sidebar taking space from the conversation.

### US5 - Inspect sources when I need them

As a user, I can expand an answer's sources on demand, so the evidence remains
available without taking space away from the answer by default.

## Functional Requirements

- **FR-001**: A new/empty chat presents context-sensitive starter prompts derived
  only from already selected context (for example: summarize selected meeting,
  list decisions, extract next actions, compare selected recordings). Starters
  are suggestions, never automatic messages or provider calls.
- **FR-002**: The composer supports multiline drafting; Enter sends only when the
  input has focus and is valid, while Shift+Enter inserts a newline. The UI makes
  this behavior discoverable and preserves an unsent draft across non-destructive
  view changes such as float/dock, minimize/restore, and sidebar synchronization.
- **FR-003**: Before sending, the chat shows a compact human-readable context
  summary (records, date/week, tags, notebooks, and task scope), with a way to
  inspect and remove a selected item through existing context-management flows.
  It must not expose unselected data merely to fill a summary.
- **FR-004**: While a request is pending, the exact user message and visible
  pending state remain in the conversation. The composer provides Cancel and
  prevents accidental duplicate submits. Cancellation restores an editable draft
  and does not persist a fabricated assistant response.
- **FR-005**: A failed request renders a clear, safe error state with Retry and
  Edit actions. Retry uses the same user message and a freshly composed current
  context; Edit returns the text to the composer without duplicating the message.
- **FR-006**: Each completed assistant answer exposes Copy and a contextual
  follow-up action. It exposes Sources when source/provenance metadata is
  available, including title, stable source identity, relevant excerpt/role, and
  navigation to an accessible source. If no sources were used or retrieval was
  degraded, the UI explains that state without inventing citations.
- **FR-007**: Session history supports local search by title and message text,
  with deterministic ordering and empty-state feedback. Search is local to
  persisted sessions and must not call an AI provider or RAG service.
- **FR-008**: Chat actions have keyboard focus, accessible names, status feedback,
  and readable light/dark contrast. Long messages, failed markdown rendering, and
  malformed stored session data degrade safely without losing usable history.
- **FR-009**: Existing session/context persistence remains backward compatible.
  New transient UI state (draft, pending/cancelled request) is not represented as
  a completed assistant turn; explicit draft persistence, if later added, needs
  its own versioned contract.
- **FR-010**: Floating and docked chat implement the same composer, context,
  source, and response-action semantics. Moving between modes neither restarts a
  request nor loses its associated session/context state.
- **FR-011**: Chat context controls are integrated into the existing right-hand
  accordion as an interactive, clearly labeled section for the active tabbed
  chat. The chat pane no longer shows its own parallel context panel or collapsed
  context rail. The section retains selected records, date/week, tags, notebooks,
  app synchronization, add/remove/reset actions, and clear-history access. It
  edits the active chat's context directly; changing tabs updates the section
  without carrying selections into another chat. Hiding or reopening the section
  does not change selected context, the draft, or session state.
- **FR-012**: Sources for each completed answer are collapsed by default and
  represented by a compact, keyboard-accessible disclosure attached to that
  answer, with a source count and clear expanded/collapsed state. Expanding one
  answer reveals only its source titles, roles, excerpts, retrieval status, and
  available navigation actions. Collapsing restores conversation space. Sources
  do not auto-expand when an answer completes or a chat opens, including a saved
  chat. An answer without usable sources shows a concise, honest status; degraded
  retrieval remains explicit without inventing citations.
- **FR-013**: The compact context summary remains visible near the composer.
  Its edit action opens and focuses the active chat's context section in the
  right sidebar. In floating mode, where that sidebar is outside the floating
  chat, the same action opens a temporary context editor without adding a
  permanent second rail. Floating, docking, and minimizing preserve context and
  drafts; the active tab's sidebar never displays a different chat's context.

## Interaction Rules For The UX Amendment

- Entering a chat tab reveals its context section in the existing right sidebar.
  The user can switch to other sidebar sections and return to context; leaving
  chat restores the previous non-chat sidebar section.
- **Edit context** opens and focuses that section without opening a removal menu.
  **Remove context…** is a separate sidebar action that offers per-item removal;
  add and reset remain separate actions as well.
- Context changes made from the right sidebar immediately update the compact
  summary and the context used by the next request. The active request keeps the
  context snapshot with which it started.
- The source disclosure belongs to one assistant answer and is placed with that
  answer's actions. Its count and label remain visible when collapsed; opening
  another answer's sources does not mix source lists.
- Saved conversations reconstruct the same answer-to-source association while
  starting with every source disclosure collapsed. Missing or malformed source
  metadata degrades to an honest, compact status.

## Architecture Boundaries

- `src/ui/chat/` owns presentation-state helpers, composer behavior, response
  actions, source rendering, and history-search policy; `ChatWidget` remains the
  compatible visible façade. Source disclosure is keyed to each assistant
  message, rather than appended to a global widget below the composer.
- `src/ui/chat/conversation_runtime.py` remains owner of one active worker,
  provider validation, signal wiring, cancellation, and cleanup. This spec may
  extend its UI-facing state but must not reimplement provider execution.
- `src/ui/chat/context_builder.py` and SPEC-008 remain source of truth for
  context selection/serialization. Source provenance is consumed from SPEC-019;
  unavailable provenance is displayed honestly.
- `src/ui/main_window/` continues to own tab/floating lifecycle and session
  sidebar coordination. Its existing `chat_context` accordion section becomes
  the interactive view of the active tab's context; context selection and
  persistence remain owned by that chat. Search should use session persistence
  via an injected port, retaining `DBManager` compatibility.

## Acceptance Criteria

1. Given an empty chat with selected recordings, when it opens, then it shows
   relevant starter prompts; selecting one fills or sends only after the user’s
   explicit confirmation/action.
2. Given a multiline draft, when Shift+Enter is pressed, then a newline is added;
   when Enter is pressed with valid input, then exactly one request starts and
   duplicate submits are blocked while it is pending.
3. Given a pending request, when Cancel is chosen, then its worker is cancelled
   through the existing runtime, the draft is available for editing, and no false
   assistant message is stored.
4. Given a failed request, when Retry is selected, then one new request uses the
   original message and current normalized context; when Edit is selected, then
   the original message returns to the composer without duplicate history.
5. Given provenance-bearing context, when a response completes, then Sources
   identifies usable records/excerpts and navigation opens the source; given
   degraded or absent retrieval, then the UI says so rather than showing a fake
   citation.
6. Given a saved session history, when a local search matches title/body text,
   then matching sessions are displayed in deterministic order without an AI/RAG
   request; no match renders an explanatory empty state.
7. Given a chat is floated, minimized, restored, and docked while a draft exists,
   then the draft, visible context summary, and session identity remain intact.
8. Given a chat is open, when the user opens the right-hand sidebar, then the
   context controls appear within its existing accordion and no second context
   sidebar is shown. Changing a filter there updates the active chat's summary
   and the next request's context; hiding/reopening the section preserves it.
9. Given an answer has sources, when it first appears, then its source details
   are collapsed beside that answer's actions and the answer remains readable;
   when the user activates the disclosure, then only that answer's source details
   and navigation are available and can be collapsed again.
10. Given an answer has no usable sources or retrieval was degraded, when it is
    displayed, then the existing honest status is accessible without presenting
    a misleading expandable citation list.
11. Given two chat sessions with different selected contexts, when the user
    changes tabs or returns from a non-chat tab, then the right sidebar shows
    only the active chat's context and the previous non-chat section is restored
    when chat is left.
12. Given a floating chat, when the user chooses to edit its context, then a
    temporary editor exposes the same actions without a permanent second rail;
    docking it preserves the selected context and draft.
13. Given a saved conversation with multiple sourced answers, when reopened,
    then every answer's own source disclosure starts collapsed and expands to
    the sources persisted for that answer, without duplicating another answer's
    sources.

## Test Plan

- Unit: starter selection, composer key handling, draft/pending/failure state,
  source-state shaping, response actions, local session-search ordering, and
  accessible labels.
- UI: focus order, disabled/pending controls, light/dark rendering, context
  summary removal entry points, malformed-message fallback, and tab/floating
  parity; verify context uses the single right-hand sidebar and per-answer
  sources are collapsed by default with keyboard-operable expansion/collapse.
- Integration: temporary SQLite plus real Qt signals verifies a context-bearing
  request → deterministic worker double → persisted response/provenance → source
  navigation; also covers cancellation, retry, and draft preservation across
  float/dock. External AI/RAG remain deterministic doubles.
- Full suite: required because changes cross chat UI/signals, worker lifecycle,
  session persistence, context synchronization, and main-window floating state.
- Amendment validation: focused chat UI tests plus real Qt interaction coverage
  for sidebar visibility, active-chat context editing, tab/floating state, and
  per-answer source disclosure after response and reload; run the full suite
  because chat layout and source presentation are shared UI.

## Documentation

- Update README and README_ES chat descriptions and user-facing keyboard/help
  documentation when implementation begins; keep README_AST aligned with the
  same user-facing behavior.
- Register implementation status in `specs/README.md`.

## Implementation Notes

- Gemini and Ollama chat use their asynchronous SDK clients inside the existing
  Qt worker. Cancel cancels the in-flight async operation, closes its HTTP client,
  suppresses completion, and restores the draft. Third-party providers that only
  expose the legacy synchronous `chat` method remain supported but cannot be
  interrupted while that synchronous call is running.
- Source metadata is stored as optional fields on assistant messages. Older
  session messages retain their original `{role, content}` shape and render an
  honest no-provenance state.
