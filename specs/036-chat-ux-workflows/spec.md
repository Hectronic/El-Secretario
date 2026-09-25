# SPEC-036: Useful And Intuitive Chat Workflows

Status: Proposed
Owner: Chat user experience
Last updated: 2026-09-25

## Problem

The chat already persists sessions and composes context, but users can still be
uncertain about what to ask, what content will be used, whether a response is in
progress, and how to act on a useful answer. The chat needs a calmer, more
discoverable workflow that makes context, response state, evidence, and common
follow-up actions explicit.

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

## Architecture Boundaries

- `src/ui/chat/` owns presentation-state helpers, composer behavior, response
  actions, source rendering, and history-search policy; `ChatWidget` remains the
  compatible visible façade.
- `src/ui/chat/conversation_runtime.py` remains owner of one active worker,
  provider validation, signal wiring, cancellation, and cleanup. This spec may
  extend its UI-facing state but must not reimplement provider execution.
- `src/ui/chat/context_builder.py` and SPEC-008 remain source of truth for
  context selection/serialization. Source provenance is consumed from SPEC-019;
  unavailable provenance is displayed honestly.
- `src/ui/main_window/` continues to own tab/floating lifecycle and session
  sidebar coordination. Search should use session persistence via an injected
  port, retaining `DBManager` compatibility.

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

## Test Plan

- Unit: starter selection, composer key handling, draft/pending/failure state,
  source-state shaping, response actions, local session-search ordering, and
  accessible labels.
- UI: focus order, disabled/pending controls, light/dark rendering, context
  summary removal entry points, malformed-message fallback, and tab/floating
  parity.
- Integration: temporary SQLite plus real Qt signals verifies a context-bearing
  request → deterministic worker double → persisted response/provenance → source
  navigation; also covers cancellation, retry, and draft preservation across
  float/dock. External AI/RAG remain deterministic doubles.
- Full suite: required because changes cross chat UI/signals, worker lifecycle,
  session persistence, context synchronization, and main-window floating state.

## Documentation

- Update README and README_ES chat descriptions and user-facing keyboard/help
  documentation when implementation begins.
- Register implementation status in `specs/README.md`.
