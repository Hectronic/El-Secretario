# Implementation Plan: Pomodoro Sessions And Activity Timeline

**Branch**: `034-pomodoro-timeline` | **Status**: Implemented

## Delivery Outline

1. Add repository contracts and migration-safe persistence for Pomodoros, notes,
   and idempotent timeline events.
2. Build a timer service with injected monotonic clock, recovery state, and
   notification port; cover it before connecting Qt.
3. Add Pomodoro and note-capture UI, reusing approved audio capture/playback
   boundaries and respecting configured STT policy for opt-in transcription.
4. Add the timeline read model, global filter synchronization, and source
   navigation.
5. Add real-SQLite/real-Qt integration coverage, run focused tests then the full
   suite, and update English and Spanish documentation.

## Integration Boundary Decision

This feature crosses UI/signals, persistence, timer lifecycle, audio capture,
and notifications. It requires integration tests; mock-only tests are not
sufficient.

## Delivered Ownership

- `src/app/pomodoro/`: focus, breaks, recovery, and audio-note capture.
- `src/persistence/productivity.py`: source aggregates and timeline read model.
- `src/ui/pomodoro/`, `src/ui/timeline/`: focused views.
- `src/ui/main_window/productivity.py`: window-level timer, completion feedback,
  recovery dialogs, and source navigation.
- No existing source file was moved; the existing recording, notebook STT,
  and tray contracts were reused through their public interfaces.
