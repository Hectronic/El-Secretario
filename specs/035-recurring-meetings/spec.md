# SPEC-035: Recurring Meetings, Prepared Metadata, And Reminders

Status: Proposed
Owner: Calendar and recording workflows
Last updated: 2026-09-25

## Problem

Users repeatedly prepare the same meetings, but currently must recreate the
title and tags and remember to begin each capture manually. They need locally
scheduled recurring meeting templates that reliably notify them and prepare a
recording with the expected metadata, without requiring an external calendar.

## Scope

- In scope: recurring-meeting templates, local recurrence calculation, occurrence
  state, reminder scheduling, notification actions, prefilled recording title and
  tags, calendar/timeline visibility, editing/pausing/deleting templates, and
  missed-reminder recovery.
- Out of scope: Google/Outlook/CalDAV sync, attendee invitations, video calls,
  automatic meeting capture, shared/team calendars, and importing arbitrary RRULE
  files in the first release.

## User Stories

### US1 - Schedule a reusable meeting

As a user, I can define a recurring meeting with a title, tags, time zone,
duration, and recurrence, so repeated meetings require no repeated setup.

### US2 - Receive an actionable reminder

As a user, I receive a reminder before each occurrence, so I can start a
prepared recording, snooze it, or dismiss it without the app recording on my
behalf.

### US3 - Preserve the meeting’s context

As a user, when I start from a reminder or scheduled occurrence, the recording
form already has the meeting title and tags, so the saved material is easy to
find later.

## Functional Requirements

- **FR-001**: A recurring-meeting template has a required title, optional
  normalized tags, local start time, IANA time zone, expected duration, reminder
  lead time, enabled/paused state, and recurrence rule.
- **FR-002**: First release recurrence options are daily, weekly on one or more
  weekdays, and monthly on a day-of-month. Each rule supports a start date and
  optional end date or occurrence count. Invalid dates (for example the 31st in
  a short month) skip that month rather than silently moving to a different day.
- **FR-003**: Recurrence calculation is time-zone aware. For ambiguous or missing
  local times at daylight-saving transitions, the UI shows the resolved next
  occurrence and uses a documented deterministic policy: first valid local time
  for an ambiguous instant, and the first valid instant after a missing one.
- **FR-004**: The scheduler materializes stable occurrences for a rolling future
  window and deduplicates by template ID plus scheduled local occurrence. Editing
  a template changes only future, unstarted occurrences after explicit user
  confirmation; historical, dismissed, missed, and started occurrences remain
  immutable records.
- **FR-005**: An occurrence moves through `scheduled`, `notified`, `snoozed`,
  `dismissed`, `missed`, `started`, `completed`, or `cancelled`. A notification
  must be emitted at most once per occurrence/lead-time version, except after an
  explicit snooze.
- **FR-006**: Reminder actions are Start recording, Snooze, Dismiss, and Open
  details. Start recording opens the existing recording flow with title and tags
  prefilled, records the occurrence ID as provenance, and never begins microphone
  capture without a user action.
- **FR-007**: Snooze choices are 5, 10, or 15 minutes. Dismissed occurrences do
  not notify again. If the app was closed or asleep at the reminder time, startup
  marks it missed and offers a single in-app catch-up card; it does not replay a
  stale system notification.
- **FR-008**: A calendar/date view shows upcoming occurrences and can open their
  details. The timeline may show planned, started, and completed occurrence
  events using the timeline read model from SPEC-034, while the template and
  occurrence remain the source of truth.
- **FR-009**: A completed recording started from an occurrence retains the
  prefilled title/tags unless the user edits them and preserves the occurrence
  link. Manual recordings never acquire a recurrence link automatically.
- **FR-010**: Scheduler and notification adapters are injectable. If the system
  tray is unavailable, reminders fall back to visible in-app state; if the app is
  not running, no unsupported background-daemon guarantee is implied.
- **FR-011**: Pausing, deleting, or changing a template cancels pending local
  reminder timers safely. It never cancels an already-started recording.

## Data Contract

```text
RecurringMeeting:
  id, title, tags[], timezone, local_start_time, expected_duration_seconds,
  recurrence_kind, recurrence_payload, starts_on, ends_on?, occurrence_limit?,
  reminder_lead_seconds, enabled, created_at, updated_at

MeetingOccurrence:
  id, recurring_meeting_id, scheduled_at_utc, scheduled_local,
  state, reminder_at_utc, snoozed_until_utc?, notification_revision,
  recording_id?, created_at, updated_at
```

The recurrence payload is versioned and validated before saving. Unique identity
for an unedited scheduled occurrence is `(recurring_meeting_id, scheduled_at_utc)`.
Template deletion follows the existing safe-delete policy and retains historical
occurrences as non-reschedulable history when they link to a recording.

## Interaction And Edge Rules

- The next three upcoming occurrences and their local time zone are always visible
  in template details.
- A duplicate Start action from UI, tray, or a delayed notification must open or
  focus the same prepared recording flow rather than create two captures.
- Editing tags/title in a prepared occurrence affects only that occurrence unless
  the user explicitly chooses “update future meetings.”
- If a recurrence has ended or reached its limit, no new occurrences or timers
  are created; completed history remains visible.
- System-clock changes trigger a safe scheduler recalculation and revalidation of
  pending reminders without duplicate notifications.

## Architecture Boundaries

- `src/app/scheduling/` should own recurrence evaluation, rolling materialization,
  catch-up, state transitions, and scheduler lifecycle independently of Qt.
- `src/persistence/` should own templates and occurrence repositories; retain the
  compatible `DBManager` façade during migration.
- A focused `src/ui/meetings/` package should own template/occurrence editor and
  list presentation. Main-window coordination owns opening prepared capture
  flows, not the scheduler.
- Reuse existing recording lifecycle and the injectable tray/notification port
  patterns from SPEC-015. Calendar synchronization remains governed by SPEC-009.
- Timeline display depends on SPEC-034’s shared read model, but scheduling and
  reminders must work when timeline UI is not yet enabled.

## Acceptance Criteria

1. Given a weekly Monday 09:00 meeting in Europe/Madrid with title and tags, when
   its next occurrence is opened, then its local/UTC time and metadata are
   accurate and the next three dates are displayed.
2. Given a reminder lead of 10 minutes, when an enabled occurrence becomes due,
   then one reminder offers Start, Snooze, Dismiss, and Open details; it does not
   start audio capture itself.
3. Given Start is selected twice through different UI routes, when preparation is
   active, then only one prepared recording flow exists and it contains the
   occurrence’s title, tags, and provenance link.
4. Given a dismissed occurrence, when its scheduled time passes or the scheduler
   restarts, then it produces no further reminder.
5. Given the app was closed at the reminder time, when it starts after the
   occurrence, then the occurrence is marked missed and one in-app catch-up card
   is available without a duplicate tray alert.
6. Given the user updates a template’s title/tags and chooses future occurrences,
   when the update persists, then past linked recordings retain original metadata
   and only future unstarted occurrences change.
7. Given a DST transition, when the rule’s local time is ambiguous or absent,
   then the documented resolution is used and no occurrence is duplicated.

## Test Plan

- Unit: recurrence expansion, end/limit handling, DST resolution, rolling-window
  idempotency, state transitions, snooze/dismiss, and clock-change recalculation.
- UI: validation, preview of next occurrences, edit-future confirmation, prepared
  recording presentation, and accessible reminder actions.
- Integration: temporary SQLite plus real Qt signals verifies persisted template
  → scheduler reminder → one prepared recording flow → saved recording provenance;
  deterministic clock/tray/audio doubles replace platform/hardware edges only.
- Full suite: required because this crosses persistence, scheduling lifecycle,
  notifications, main-window UI/signals, calendar, and recording workflows.

## Documentation

- Update README and README_ES with local-only scheduling scope and reminder
  behavior, including the lack of external calendar sync/background-daemon
  guarantee.
- Register implementation status in `specs/README.md`.
