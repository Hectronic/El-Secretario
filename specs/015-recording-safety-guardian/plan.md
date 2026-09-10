# Implementation Plan: Recording Safety Guardian

**Branch**: `015-recording-safety-guardian` | **Status**: Planned | **Spec**: [spec.md](spec.md)

## Summary

Add a feature-local recording guardian that observes capture state, elapsed time,
and voice-activity events. It publishes tray status and rate-limited reminders
through injectable platform ports, while existing capture code remains the only
owner of actual stop/save operations.

## Technical Context

**Language**: Python 3.12 / PyQt6  
**Platforms**: Windows, Ubuntu, macOS  
**Testing**: pytest + pytest-qt; offscreen Qt; deterministic tray/notification and
audio-activity doubles.

## Design Decisions

- Put state policy under `src/ui/recording_in_progress/` or a narrow application
  service, not in `MainWindow`.
- Use `QSystemTrayIcon` only behind an availability-aware adapter.
- Reuse existing voice-activity/audio-level signals if available; do not create a
  second audio capture pipeline.
- Persist preferences through the existing settings boundary.

## Constitution Check

Requires real Qt lifecycle integration tests, explicit cleanup, and no platform
assumption that a tray is present.
