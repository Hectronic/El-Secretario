# SPEC-038: Contextual System Tray Quick Actions

Status: Proposed
Owner: System tray interactions
Last updated: 2026-09-25

## Problem

The persistent tray icon currently provides Show/Hide, Quit, and controls while
a recording is active. Starting a recording, capturing a quick note, opening a
scheduled meeting, or checking a Pomodoro still requires navigating the main
window. The menu should make frequent actions available directly while showing
only actions that make sense in the current state.

## Scope

- In scope: state-aware tray menu, Start recording, active recording controls,
  quick text/audio note entry points, Pomodoro controls when SPEC-034 is
  available, next recurring meeting when SPEC-035 is available, navigation to
  timeline/tasks/settings, status text, shortcuts, and graceful tray fallback.
- Out of scope: a second recording engine, automatic microphone capture from a
  reminder, running the app as a background service after exit, and duplicating
  the full Settings or task board inside the tray menu.

## User Stories

### US1 - Start recording without opening the full workspace

As a user, I can deliberately start a new recording from the tray with the
configured devices and see confirmation or a clear error immediately.

### US2 - Control ongoing work

As a user, I can see elapsed recording/focus status and pause, resume, or safely
stop the active activity from the same menu.

### US3 - Capture or open the next thing

As a user, I can create a quick note, open the next meeting, or jump to my
timeline, tasks, or settings with a single menu choice.

## Menu Model

| State | Primary actions | Status and supporting actions |
| --- | --- | --- |
| Idle | Start recording; New text note; New audio note | Next meeting if scheduled; Start Pomodoro if available; Open app; Timeline; Tasks; Settings; Quit |
| Recording | Pause/Resume; Stop and save; Cancel with confirmation | Recording title and elapsed time; Open recording; supporting navigation |
| Pomodoro active | Start recording if no capture is active; Pomodoro Pause/Resume, Finish, Cancel | Focus title and remaining time; notes/timeline navigation |
| Meeting due | Start prepared recording | Meeting title/time, Snooze, Dismiss, Open details |

Recording state has priority in the top status row; a simultaneous Pomodoro
remains visible in its own subsection. Quit stays separated at the end of the
menu. Unavailable feature actions are absent, not dead controls.

## Functional Requirements

- **FR-001**: The tray menu is derived from one current application-state
  snapshot. It refreshes when opened and after recording, Pomodoro, or meeting
  state changes; stale or destroyed widget references cannot remain callable.
- **FR-002**: Start recording is an explicit tray action. If a validated default
  microphone/capture configuration is available, it starts through the existing
  recording coordinator and gives immediate status feedback. If setup or device
  permission is needed, it opens the prepared recording flow focused on that
  problem and does not claim capture started.
- **FR-003**: Start recording from a due meeting uses its prepared title/tags and
  occurrence link from SPEC-035. Generic Start recording uses normal defaults;
  neither path overwrites an already active capture.
- **FR-004**: The existing Pause/Resume, Stop and save, and Cancel actions route
  through the same guarded recording lifecycle as the main UI. Stop/save is
  idempotent and Cancel requires an explicit confirmation because it discards
  capture. Disabled, busy, and terminal states have accurate labels and actions.
- **FR-005**: New text note opens a compact titled editor. New audio note opens
  the existing capture flow with the note type selected; recording hardware
  contention is checked and explained. Notes are saved by their feature owner,
  not by a tray-specific storage path.
- **FR-006**: When SPEC-034 is available, the tray shows the active Pomodoro
  title/remaining time plus Start, Pause/Resume, Finish, and Cancel actions
  appropriate to its state. Commands use the Pomodoro service and cannot create
  duplicate completion events.
- **FR-007**: When SPEC-035 is available, the tray shows at most the next
  relevant occurrence and exposes Start prepared recording, Snooze, Dismiss, and
  Open details when its reminder is due. A tray action and in-app reminder share
  the same occurrence state and deduplication guard.
- **FR-008**: Open app, Timeline, Tasks, and Settings raise/focus the appropriate
  existing window/tab. A capability that is not installed or enabled is hidden;
  menu layout remains usable on platforms with limited tray-menu support.
- **FR-009**: Tooltip/menu status shows the active recording or Pomodoro without
  exposing private note text, credentials, or a full transcript. Recording
  indicator remains visible whenever capture is active.
- **FR-010**: If a tray is unavailable, the same essential actions remain
  available from the main UI, and a failed tray action yields in-app status.
  Closing the app via Quit cleans up tray references, timers, and active menu
  callbacks through existing shutdown policy.
- **FR-011**: The user can choose whether nonessential tray notifications are
  shown in Settings; safety and meeting reminder policies remain owned by their
  respective features.

## Architecture Boundaries

- `src/ui/system_tray_manager.py` remains the Qt tray façade. A focused menu
  state/presenter helper may build actions from immutable application-state
  snapshots; feature commands are dispatched to existing main-window/application
  coordinators.
- Recording lifecycle and guardian safety remain with SPEC-001/015;
  persistent tray icon and badge remain with SPEC-020.
- Pomodoro, timeline, and recurring-meeting commands remain with SPEC-034/035.
  This spec only exposes their actions when implemented and available.
- Settings entry points and notification preferences follow SPEC-037/013.

## Acceptance Criteria

1. Given an idle app with a working default microphone, when Start recording is
   chosen from the tray, then exactly one capture starts, the icon/status changes
   to recording, and pause/stop/cancel actions become available.
2. Given the microphone is unavailable or permission is denied, when Start is
   chosen, then no false recording state is shown and the user sees a recoverable
   in-app explanation and setup path.
3. Given a recording is already active, when the menu is reopened, then Start is
   unavailable; Stop and save from the tray goes through one guarded save flow.
4. Given a user chooses Cancel recording, when they decline confirmation, then
   capture continues; when they confirm, the existing cancellation flow runs once.
5. Given a Pomodoro is paused, when the tray menu opens, then Resume and Finish
   are offered and its status matches the main UI. Finishing writes one timeline
   event even if the menu action is triggered twice.
6. Given a meeting reminder is due, when Start prepared recording is chosen from
   the tray, then its title/tags and occurrence link reach the recording flow;
   Snooze or Dismiss use the same persistent occurrence as the in-app reminder.
7. Given tray support disappears or the app quits, when menu cleanup runs, then
   no stale callbacks fire and essential controls remain available in the app
   whenever it is running.

## Test Plan

- Unit/UI: menu composition by application state, action enabled/visibility
  rules, status labels, double-dispatch guards, cancel confirmation, and cleanup.
- Integration: temporary SQLite plus real Qt signals in offscreen mode verifies
  tray Start → recording coordinator → saved recording/status, and conditional
  Pomodoro/meeting action → persisted timeline/occurrence state. Only tray
  platform, clock, and audio hardware/network edges use deterministic doubles.
- Full suite: required because this crosses Qt menu/signals, recording lifecycle,
  persistence, notifications, and future scheduling/timer boundaries.
- Manual: verify menu behavior and focus handling on Windows, Ubuntu, and macOS,
  including desktops without a usable system tray.

## Documentation

- Update README and README_ES with quick actions, recording safety, and platform
  fallback when implementation begins.
- Register implementation status in `specs/README.md`.
