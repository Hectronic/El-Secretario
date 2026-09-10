# Tasks: Recording Safety Guardian

## Phase 1: Design and State

- [x] T001 Define recording guardian state, settings defaults, and notification rate limits.
- [x] T002 Define an availability-aware tray/notification adapter and cleanup contract.

## Phase 2: User Story 1 - Tray Visibility

- [x] T003 [US1] Implement one active-recording tray indicator and safe action dispatch.
- [x] T004 [US1] Add Qt integration coverage for start, duration update, stop/save, and cleanup.

## Phase 3: User Story 2 - Duration Reminders

- [x] T005 [US2] Implement configurable prolonged-recording reminders.
- [x] T006 [US2] Add deterministic timer and notification unit/integration tests.

## Phase 4: User Story 3 - Silence Warning

- [x] T007 [US3] Connect existing activity signals to configurable inactivity warnings.
- [x] T008 [US3] Implement opt-in automatic stop only after warning policy is accepted.
- [x] T009 [US3] Add silence/recovery/terminal-state integration tests.

## Phase 5: Validation

- [x] T010 Validate availability-aware tray fallback with deterministic platform edges and run the full suite.
- [x] T011 Add branded tray icon plus pause/resume and cancel actions, with lifecycle integration coverage.

## Definition of Done

- Default silence behavior cannot stop a recording.
- Tray, notification, and stop ports are injectable and deterministic in tests.
- Existing stop/save flow is invoked once and remains the only persistence owner.
- Timers, signal connections, and tray state are cleaned up for success, failure,
  cancellation, and application shutdown.
