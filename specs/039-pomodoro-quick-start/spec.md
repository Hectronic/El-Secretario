# SPEC-039: Simple Pomodoro And Unified Activity Discovery

Status: Proposed
Owner: Productivity workflows
Related: SPEC-034 Pomodoro Sessions And Activity Timeline; SPEC-006 RAG Search; SPEC-007 Chat Sessions
Last updated: 2026-09-27

## Problem

Pomodoro already records sessions and notes, but the screen exposes timer setup,
breaks, metadata, text notes, and audio-note controls at once. Starting focus
also requires opening a separate tab and entering a title. Meanwhile, activity
is split across the shared timeline, meeting views, summaries, general search,
and chat context. Users need one obvious way to start focus and one chronological
place where Pomodoros appear and can be found and discussed alongside the rest
of their work.

## Goal

Simplify the Pomodoro screen and make Pomodoro sessions first-class items in the
application's single general activity timeline, search, and chat context. Add a
visible Welcome-page quick-start while continuing to use the existing Pomodoro
service, timer, persistence, breaks, recovery, and source aggregates from
SPEC-034.

## Scope

- In scope: a prominent Welcome-page Pomodoro action; a focused, simpler timer
  screen; one chronological general activity timeline containing Pomodoros,
  meetings, daily/weekly summaries, and other existing activity types; and
  discoverability of Pomodoro sessions and notes in global search and selected
  chat context.
- Out of scope: replacing the full Pomodoro view, changing timer or persistence
  semantics, changing break behavior, adding a Pomodoro-only timeline, duplicating
  summary/meeting/Pomodoro storage, or changing summary generation and RAG policy.

## User Stories

### US1 - Start focus without setup friction

As a user on the Welcome page, I can start a standard focus interval with one
click, so I can begin working without first opening a tab or filling a form.

### US2 - Return to the active timer

As a user, I can see when a Pomodoro is active and open its existing controls
from Welcome, so I can check or manage the same timer without creating another.

### US3 - Review all work in one chronology

As a user, I can see Pomodoros, meetings, daily and weekly summaries, and other
activity together in chronological order, so I do not have to switch between
feature-specific timelines to understand my work.

### US4 - Find and discuss a Pomodoro

As a user, I can find Pomodoro sessions and their saved notes through general
search and explicitly add them to chat context, so they work like other
discoverable app content.

### US5 - Focus on the timer

As a user, I see the remaining time and the few controls I need first, while
optional metadata, breaks, and note capture stay available without crowding the
main focus workflow.

## Functional Requirements

- **FR-001**: Welcome presents a prominent, keyboard-accessible Pomodoro action
  in its primary action area. It remains visible in supported responsive layout
  densities and does not require scrolling to discover on a normal window size.
- **FR-002**: When no focus or break is running or paused, activating the action
  opens or reuses the existing Pomodoro view and immediately starts one focus
  interval. It does not show a setup dialog.
- **FR-003**: Quick start uses the saved `pomodoro/focus_minutes` duration (the
  existing default remains 25 minutes) and a localized default title such as
  “Quick focus”. The title remains editable in the full Pomodoro view; tags are
  optional and default to empty.
- **FR-004**: If a focus interval or break is already running or paused, activating
  the Welcome action opens the existing Pomodoro view and does not start a second
  interval or silently change the current one. Welcome presents the active state
  and remaining time while it is visible.
- **FR-005**: The Welcome action reflects lifecycle changes from the existing
  `PomodoroService` and `BreakService`, including pause, resume, finish, cancel,
  completion, and restart recovery. It must not introduce a second timer owner or
  independently calculate elapsed time.
- **FR-006**: Starting through Welcome follows the same validation, persistence,
  completion notification, restart-recovery, and timeline behavior as starting
  from the full Pomodoro view. Failure leaves the timer state unchanged and gives
  visible feedback.
- **FR-007**: Closing the Pomodoro tab or moving between tabs does not stop the
  active service. The Welcome action can reopen the same timer and its current
  controls.
- **FR-008**: This feature does not duplicate Pomodoro, meeting, note, or summary
  source aggregates. Existing SPEC-034 behavior remains the source of truth for
  focus, breaks, notes, audio, and Pomodoro lifecycle. Any shared timeline/search
  read-model change must be additive and preserve existing persistence APIs.
- **FR-009**: Pomodoro sessions appear as ordinary typed items in the one general
  chronological activity timeline, alongside meetings, daily and weekly
  summaries, and other supported activities. There is no separate Pomodoro
  timeline or Pomodoro-only chronological history.
- **FR-010**: The shared activity timeline orders all item types by their
  occurrence time, with a deterministic tie-breaker. Existing date/week/tag
  filters apply consistently to Pomodoros, meetings, summaries, and other
  timeline items. Selecting an item opens its owning detail/source.
- **FR-011**: General search can match Pomodoro title, tags, and associated saved
  text/audio-note metadata or transcription when available. It can also match
  meeting and daily/weekly summary content. Results identify their item type and
  navigate to the existing owning view; no duplicate source records are created.
- **FR-012**: Chat context management can explicitly select a Pomodoro session
  and its associated notes. The selected context exposes title, date, tags, and
  available note content; unselected sessions are not added just to fill
  context. Chat suggestions and search results never send a message or invoke a
  provider automatically.
- **FR-013**: The primary Pomodoro view prioritizes remaining time and essential
  start/pause/resume/finish/cancel controls. Less frequent setup and capture
  options (duration, title/tags, break controls, text/audio notes, transcription
  preference) are organized behind clear secondary sections or progressive
  disclosure and remain reachable.
- **FR-014**: Daily and weekly summaries enter the general activity timeline as
  references to their existing persisted summaries, with stable source identity
  and the date/week they represent. Updating a summary updates its activity item
  rather than adding duplicate rows.

## Interaction Rules

- Idle label: “Start Pomodoro” (localized).
- Active label: “Open active Pomodoro”; Welcome also shows its current state and
  remaining time. The click opens the same timer view.
- Paused state remains paused when opened. The user resumes using the existing
  Pomodoro controls.
- Starting from Welcome does not force a title prompt, tag prompt, or duration
  prompt. The default title and saved duration are visible/editable after opening
  the Pomodoro view.
- A break counts as an active interval for duplicate prevention and routes to
  its existing controls.
- Pomodoros are rendered inside the general activity timeline beside meetings
  and daily/weekly summaries. The application does not add a Pomodoro-specific
  timeline entry point.
- Secondary Pomodoro tools remain available but do not compete visually with the
  current timer and its essential controls.

## Architecture Boundaries

- `src/ui/welcome/` owns only the quick-start action and presentation of the
  shared timer state; it emits an intent rather than constructing a timer.
- `src/ui/main_window/productivity.py` coordinates the Welcome intent, opens or
  selects the existing Pomodoro tab, and asks its widget/service to quick-start
  only when no interval is active.
- `src/app/pomodoro/` remains the sole owner of focus/break lifecycle and state.
  Do not create a second service, `QTimer`, or parallel persistence path.
- SPEC-034 remains the contract for timer recovery, SQLite persistence,
  notifications, notes/audio capture, and timeline navigation.
- The shared timeline composes references from owning repositories; it does not
  copy Pomodoro, meeting, or summary content into a new feature-specific store.
- General search and chat context extend existing search/context adapters to
  recognize Pomodoro sessions and summaries. RAG ranking/provider policy remains
  owned by its existing feature contracts.

## Acceptance Criteria

1. Given Welcome is visible and no interval is active, when the user activates
   the Pomodoro button, then exactly one focus interval starts using the saved
   duration and default title, and the existing timer view opens without a setup
   dialog.
2. Given a focus interval is running or paused, when the user activates the
   Welcome button, then the same Pomodoro is shown with its state and remaining
   time and no second interval is created.
3. Given a break is running or paused, when the user activates the Welcome
   button, then the existing break controls open and focus is not started.
4. Given the Pomodoro view is closed while its service remains active, when the
   user activates the Welcome button, then the current timer view is reopened and
   the timer has not restarted.
5. Given a quick-start failure, when it is reported, then the service remains in
   its prior state and an accessible status message explains that start failed.
6. Given responsive Welcome layouts and keyboard navigation, when the user
   reaches primary actions, then the Pomodoro action is visible, focusable, and
   has a descriptive accessible name.
7. Given meetings, summaries, Pomodoros, and notes on nearby dates, when the
   general timeline is shown, then all supported items appear in one
   deterministic chronological sequence and filters work across item types.
8. Given a Pomodoro title or associated note content, when the user searches
   generally, then the matching typed result navigates to the existing session
   or note owner.
9. Given a Pomodoro is explicitly selected as chat context, when a question is
   sent, then its selected metadata and available note content are included; an
   unselected Pomodoro is not included.
10. Given the Pomodoro screen is opened, when the timer is idle or active, then
    the timer and essential controls are the primary visual focus and optional
    setup/note tools remain available in secondary sections.

## Test Plan

- Unit: quick-start routing, idle/active/paused/break presentation, configured
  duration/default title, duplicate prevention, shared timeline ordering and
  filtering across source types, search-result shaping, and selected Pomodoro
  chat-context serialization.
- UI: Welcome button visibility and accessible name in normal/compact layouts;
  keyboard activation; timer-first visual hierarchy; secondary controls;
  feedback/navigation for idle, active, paused, and break states.
- Integration: temporary SQLite plus real Qt signals in offscreen mode verifies
  Welcome click → shared PomodoroService → general timeline entry, general search
  result, explicitly selected chat context, and navigation to the existing owner.
  It also verifies the unified timeline combines meetings, daily/weekly
  summaries, Pomodoros, and notes in deterministic chronological order.
  Deterministic clock and notification doubles may replace only those external
  boundaries.
- Regression: retain SPEC-034 Pomodoro and timeline tests, including tab closure,
  recovery, break lifecycle, and persistence.
- Full suite: required because this crosses Welcome UI/signals, MainWindow
  navigation, timer lifecycle, and persistence.

## Documentation

- When implementation begins, update README, README_ES, and README_AST to explain
  the Welcome quick-start, the single shared activity timeline, general search
  and chat discovery, and the simplified timer screen.
- Register implementation status in `specs/README.md`.
