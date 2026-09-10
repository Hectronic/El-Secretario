# Feature Specification: Recording Safety Guardian

**Feature Branch**: `015-recording-safety-guardian`  
**Created**: 2026-09-10  
**Status**: Planned  
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

## Success Criteria

- **SC-001**: A backgrounded active recording is observable within one second via
  tray state where supported.
- **SC-002**: No default configuration stops a recording solely due to silence.
- **SC-003**: Integration tests prove tray/action state and cleanup across the
  capture lifecycle with deterministic platform edges.
