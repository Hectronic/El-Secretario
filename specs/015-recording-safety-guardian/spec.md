# Feature Specification: Recording Safety Guardian

**Feature Branch**: `015-recording-safety-guardian`  
**Created**: 2026-09-10  
**Status**: Completed
**Input**: Prevent users from accidentally leaving a recording running while
keeping deliberate long recordings uninterrupted.

## User Scenarios & Testing

### User Story 1 - See an active recording outside the app window (Priority: P1)

As a user, I can see that recording remains active from the system tray, including
its elapsed duration, so minimizing or switching applications does not hide it.

**Independent Test**: With an active capture session and deterministic tray port,
assert visible status, duration updates, and stop action dispatch.

**Acceptance Scenarios**:

1. **Given** recording starts, **When** the app is backgrounded, **Then** a tray
   indicator visibly identifies the active recording and its elapsed duration.
2. **Given** the tray is available, **When** the user chooses stop and save,
   **Then** the existing recording-stop workflow runs exactly once.
3. **Given** the tray is available, **When** the user chooses pause/resume or
   cancel, **Then** the existing capture lifecycle performs that action and the
   tray reflects or cleans up the terminal state.

### User Story 2 - Receive a safe prolonged-recording reminder (Priority: P1)

As a user, I receive a non-invasive reminder after a configurable recording
duration, with an explicit choice to continue or stop and save.

**Acceptance Scenarios**:

1. **Given** recording reaches the configured threshold, **When** the reminder
   interval elapses, **Then** the user receives a notification without stopping
   capture automatically.
2. **Given** the user chooses continue, **When** the next interval is due, **Then**
   reminders remain rate-limited and recording continues.

### User Story 3 - Handle inactivity without accidental loss (Priority: P2)

As a user, I am warned when conversation has not been detected for a configurable
period, and automatic stop remains opt-in.

**Acceptance Scenarios**:

1. **Given** sustained silence, **When** its threshold is crossed, **Then** a
   warning reports the inactivity and offers continue or stop/save.
2. **Given** automatic stop is disabled, **When** silence continues, **Then** no
   recording is stopped without user confirmation.

## Edge Cases

- System tray is unavailable or disabled by the desktop environment.
- Audio input is silent because of a paused speaker, not an abandoned recording.
- The recording ends, fails, or the app shuts down while a reminder is queued.
- Multiple capture windows must never create conflicting tray indicators.

## Current Implementation Context

- `src/ui/recording_in_progress/runtime.py` owns recorder start, pause, stop,
  cancel, and amplitude-signal connection.
- `src/ui/recording_in_progress/session.py` owns elapsed-time formatting and
  the finished recording configuration payload.
- `src/ui/recording_in_progress/widget.py` owns the active capture UI.
- `src/audio.py` exposes `Recorder.amplitude_changed` and emits an RMS value
  from every audio callback.
- Main-window and recording-tab coordinators own final save and transcription
  handoff. The guardian MUST dispatch to those owners and never call
  `Recorder.stop()` directly from a tray adapter.

## Proposed Settings And State

Settings keys should be namespaced under `recording_guardian/`:

| Key | Type | Proposed default | Meaning |
| --- | --- | --- | --- |
| `enabled` | bool | `true` | enable in-app/tray observation |
| `duration_warning_enabled` | bool | `true` | enable prolonged-recording warning |
| `duration_threshold_seconds` | int | `3600` | first duration warning |
| `reminder_interval_seconds` | int | `900` | minimum interval between reminders |
| `silence_warning_enabled` | bool | `true` | enable inactivity warning |
| `silence_threshold_seconds` | int | `300` | sustained low activity threshold |
| `auto_stop_after_silence` | bool | `false` | never stop by default |

Missing or invalid values fall back to these defaults and are clamped to
positive, finite intervals.

Guardian state should be a single session object with:

```text
inactive | recording | paused | stopping | completed | failed | cancelled
started_at, last_activity_at, last_reminder_at, warning_count
```

Only `recording` and `paused` are active tray states. Terminal states cancel
timers and remove the indicator.

## Platform Ports

Define injectable ports before connecting Qt:

- `TrayPort`: availability, set status/title, show/hide, action callbacks;
- `NotificationPort`: warning/error notification with action identifiers;
- `RecordingStopPort`: one idempotent `request_stop_and_save()` operation.

The Qt adapter may use `QSystemTrayIcon`; tests use deterministic fakes. If
tray availability changes, the guardian falls back to in-app status without
changing capture state.

## Activity And Timer Rules

- Activity is refreshed only from the existing amplitude signal; no second audio
  stream or polling pipeline may be introduced.
- Paused recordings do not accumulate silence warnings.
- A reminder re-checks current state immediately before display.
- Stop/save dispatch uses a compare-and-set guard so tray, UI, and notification
  actions cannot save twice.

## Requirements

- **FR-001**: The system MUST expose one accurate active-recording tray state
  where the platform supports a system tray.
- **FR-002**: The system MUST degrade gracefully to in-app status/notifications
  when the tray is unavailable, especially on supported Linux desktops.
- **FR-003**: The system MUST offer configurable duration and silence thresholds.
- **FR-004**: Automatic stop after silence MUST be disabled by default and require
  explicit opt-in.
- **FR-005**: Tray actions and notifications MUST reuse the existing safe
  stop/save lifecycle and clean up on every terminal recording state.
- **FR-006**: The tray MUST offer pause/resume and cancel actions in addition to
  stop and save; cancel MUST discard the active capture through the existing
  cancellation lifecycle.

## Success Criteria

- **SC-001**: A backgrounded active recording is observable within one second via
  tray state where supported.
- **SC-002**: No default configuration stops a recording solely due to silence.
- **SC-003**: Integration tests prove tray/action state and cleanup across the
  capture lifecycle with deterministic platform edges.

## Required Acceptance Examples

1. Start → tray appears → elapsed text updates → stop dispatches once → tray
   disappears after the existing save flow completes.
2. Duration threshold → one warning → continue → no warning before the interval.
3. Silence threshold → warning only; default settings leave recording active.
4. Silence warning → explicit stop → exactly one existing stop/save request.
5. Tray unavailable → in-app status remains accurate without an adapter error.
6. Shutdown while active → timers, signal connections, tray state, and guardian
   references are cleaned up.
