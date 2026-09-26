# SPEC-034: Pomodoro Sessions And Activity Timeline

Status: Implemented
Owner: Productivity workflows
Last updated: 2026-09-25

## Problem

El Secretario has recordings, notes, and calendar-filtered history, but it does
not let a user deliberately track focused work or see it beside the material
created during that work. Users need a simple Pomodoro flow that creates a
trustworthy chronological record and supports text and audio notes without
turning every focus interval into a meeting recording.

## Scope

- In scope: configurable focus/break timer, start/pause/resume/finish/cancel
  lifecycle, timeline entries, text notes, audio-note capture and playback,
  titles/tags, date/tag filtering, timer-completion notification, and timeline
  navigation to linked artifacts.
- Out of scope: external calendar synchronization, team/shared timers, automatic
  productivity scoring, mandatory transcription/summarization of audio notes,
  or changes to the STT runtime policy.

## User Stories

### US1 - Complete a focused interval

As a user, I can start a Pomodoro with a title and tags, see its remaining time,
and pause, resume, finish early, or cancel it, so the timer reflects real work
rather than an idealized schedule.

### US2 - Capture context while working

As a user, I can add titled text notes and audio notes to the active Pomodoro,
so decisions and ideas remain connected to the work interval.

### US3 - Review work chronologically

As a user, I can review completed Pomodoros and their notes in a date/tag-filtered
timeline, so I can reconstruct what I worked on and open the related material.

## Functional Requirements

- **FR-001**: A new Pomodoro starts with a required non-empty title, optional
  normalized tags, and a selected duration. The default focus duration is 25
  minutes; settings may define positive focus, short-break, and long-break
  durations.
- **FR-002**: The timer state is `idle`, `running`, `paused`, `completed`, or
  `cancelled`. Only a running interval decrements elapsed time. Finishing early
  records the actual elapsed duration and an `ended_early` outcome.
- **FR-003**: Completion creates exactly one completed focus entry. Cancellation
  creates no completed Pomodoro entry, but explicitly saved notes remain as
  standalone timeline notes with their original timestamps.
- **FR-004**: A completed interval creates a timeline event containing its stable
  ID, title, tags, started/ended timestamps, planned and actual durations,
  outcome, and links to attached notes. Breaks are visible only when the user
  enables “show breaks”; they never count as completed focus time.
- **FR-005**: A text note has a required non-empty title, body, timestamps,
  optional tags, and an optional Pomodoro link. It can be created during or
  outside a timer. Saving it must not stop or reset an active timer.
- **FR-006**: An audio note has a required title, captured-at timestamp, duration,
  optional tags, and a durable local-audio reference. It can be captured during
  or outside a timer; stopping/cancelling its capture must not affect the
  Pomodoro lifecycle.
- **FR-007**: Audio notes reuse the existing audio capture, storage, playback,
  deletion, and platform-safety conventions where applicable. Automatic
  transcription is opt-in and, if chosen, must use the configured STT backend,
  device, compute type, and `force_cpu` policy.
- **FR-008**: The timeline is a chronological, paginated activity view. It shows
  Pomodoros, text notes, audio notes, and future feature-owned activity events
  through a common read model; each row exposes type, title, time, tags, and
  linked parent/source without duplicating source content.
- **FR-009**: Existing global date/week/tag selection normalizes and filters
  timeline results consistently with calendar, task, and chat context. Timeline
  selection may open the record, note, or related Pomodoro detail.
- **FR-010**: At completion, the app emits one in-app completion state and, when
  enabled and supported, one system-tray notification. Notification unavailability
  must not prevent persistence or leave the timer active.
- **FR-011**: The active timer survives view/tab changes. On orderly application
  shutdown it persists enough state to calculate elapsed time on the next start;
  after restart it must ask the user to complete or discard an overdue interval
  rather than silently fabricating completion.

## Data Contract

Persistence must keep source aggregates separate from the derived timeline read
model. A Pomodoro and note must have stable IDs; the timeline event points to
them and is idempotent per source event.

```text
Pomodoro:
  id, title, tags[], state, started_at, ended_at,
  planned_seconds, elapsed_seconds, outcome,
  created_at, updated_at

Note:
  id, kind: text | audio, title, body_or_audio_ref, duration_seconds?,
  tags[], pomodoro_id?, captured_at, created_at, updated_at

TimelineEvent:
  id, event_type, source_id, parent_source_id?, occurred_at,
  title_snapshot, tags_snapshot[], metadata
```

Deleting a note or Pomodoro must preserve referential integrity: the timeline
row is removed or rendered as an unavailable historical reference according to
the project’s existing safe-delete policy. No audio bytes are stored in SQLite.

## Interaction And Edge Rules

- Starting another Pomodoro while one is running requires an explicit choice to
  finish early, cancel, or keep the current interval; two active timers are
  never permitted.
- Title/tags on an active Pomodoro may be edited; a completed timeline event
  reflects the final saved metadata.
- A note can have its own tags in addition to inherited display tags from its
  Pomodoro. Filtering by a parent tag includes its linked notes; independent
  note tags remain queryable.
- Wall-clock changes must not make elapsed time negative or extend a timer.
  Use a monotonic clock while the process is running and persisted timestamps
  only for restart recovery.
- Timer and audio capture resources are released on every terminal state; a
  failed audio-note capture leaves a visible recoverable error and no dangling
  audio reference.

## Architecture Boundaries

- A focused `src/app/pomodoro/` service should own timer state, restart recovery,
  and completion decisions; Qt widgets only render state and dispatch actions.
- `src/persistence/` should own Pomodoro, note, and timeline repositories;
  `DBManager` remains a compatible façade until a deliberate migration.
- A `src/ui/timeline/` package should own timeline composition and navigation;
  a focused Pomodoro UI package should own timer and note-capture presentation.
- The existing recording-in-progress guardian and notification/tray adapters are
  reused through injected ports, never by duplicating platform notification code.
- Related contracts: recording metadata/audio behavior is SPEC-004; calendar
  filtering is SPEC-009; lifecycle/cleanup behavior is SPEC-017.

## Acceptance Criteria

1. Given a 25-minute Pomodoro with title and tags, when it reaches zero, then it
   becomes completed once, writes one timeline event with actual duration, and
   presents completion feedback without creating a recording.
2. Given an active Pomodoro, when the user pauses for five minutes, resumes, and
   finishes, then paused time is excluded from elapsed focus duration.
3. Given an active Pomodoro, when the user saves a titled text note and a titled
   audio note, then both persist independently, remain linked to the Pomodoro,
   and are discoverable from its timeline entry.
4. Given audio-note transcription is disabled, when an audio note is saved, then
   no STT worker is started; when enabled, its worker uses configured runtime
   preferences and does not block the timer UI.
5. Given a focused day/tag filter, when the timeline opens, then it contains only
   matching entries and opening a row reaches its source or parent detail.
6. Given the app is restarted with an overdue running interval, when recovery is
   shown, then no completion is written until the user explicitly confirms it.
7. Given tray notifications are unavailable, when a Pomodoro completes, then the
   completed event is persisted and an in-app completion state remains visible.

## Test Plan

- Unit: state transitions, duration validation, monotonic elapsed-time logic,
  restart-recovery decisions, tag normalization, timeline shaping, and audio-note
  failure cleanup.
- UI: timer controls, enabled/disabled states, title/tag validation, note forms,
  keyboard-safe timer updates, and light/dark rendering.
- Integration: temporary SQLite plus real Qt signals in offscreen mode verifies
  timer completion → persisted Pomodoro/note/timeline event → date/tag-filtered
  timeline navigation. Deterministic doubles replace only clock, tray, and audio
  hardware/STT edges.
- Full suite: required because this crosses UI/signals, persistence, timer
  lifecycle, audio capture, and notification boundaries.

## Documentation

- Update README and README_ES feature lists, settings documentation, and the
  timeline/pomodoro help text when implementation begins.
- Register implementation status in `specs/README.md`.

## Implementation And Verification

- `src/app/pomodoro/` owns monotonic focus and break state, explicit restart
  recovery, and audio-note capture. The focus service remains alive in the main
  window when its tab closes.
- `src/persistence/productivity.py` owns SQLite aggregates and an idempotent,
  paginated timeline read model; `DBManager` delegates through its compatible
  repository facade. `src/ui/pomodoro/` and `src/ui/timeline/` own the views;
  `src/ui/main_window/productivity.py` coordinates notifications and navigation.
  The global tag selector includes productivity-only tags, and deleting a
  completed Pomodoro leaves saved notes as standalone timeline entries.
- Focused tests: `tests/app/pomodoro/` and
  `tests/persistence/test_productivity_repository.py`.
- Cross-component contract: `tests/integration/test_pomodoro_timeline_flow.py`
  verifies real SQLite persistence and Qt signals across focus completion,
  text/audio notes, optional STT callback, tab closure, timeline navigation, and
  global date/tag synchronization.
  `tests/integration/test_pomodoro_main_window.py` verifies the real main-window
  buttons and shared SQLite flow. `tests/ui/notebooks/test_transcription_runtime.py`
  verifies the reused STT adapter passes saved backend, model, compute type, and
  `force_cpu` policy to the worker.
- README, README_ES, and README_AST document the new controls and recovery flow.
