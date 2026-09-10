# Tasks: Recording Safety Guardian

## Phase 1: Design and State

- [ ] T001 Define recording guardian state, settings defaults, and notification rate limits.
- [ ] T002 Define an availability-aware tray/notification adapter and cleanup contract.

## Phase 2: User Story 1 - Tray Visibility

- [ ] T003 [US1] Implement one active-recording tray indicator and safe action dispatch.
- [ ] T004 [US1] Add Qt integration coverage for start, duration update, stop/save, and cleanup.

## Phase 3: User Story 2 - Duration Reminders

- [ ] T005 [US2] Implement configurable prolonged-recording reminders.
- [ ] T006 [US2] Add deterministic timer and notification unit/integration tests.

## Phase 4: User Story 3 - Silence Warning

- [ ] T007 [US3] Connect existing activity signals to configurable inactivity warnings.
- [ ] T008 [US3] Implement opt-in automatic stop only after warning policy is accepted.
- [ ] T009 [US3] Add silence/recovery/terminal-state integration tests.

## Phase 5: Validation

- [ ] T010 Validate Windows, Ubuntu, and macOS tray fallback behavior and run the full suite.
