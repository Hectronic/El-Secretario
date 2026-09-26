# Implementation Plan: Contextual System Tray Quick Actions

**Branch**: `038-tray-quick-actions` | **Status**: Proposed

## Delivery Outline

1. Characterize current tray menu and recording coordinator behavior with
   focused tests; define an application-state snapshot and action ownership map.
2. Add idle Start recording and navigation actions through existing coordinators,
   with device preflight, duplicate-start guard, and visible feedback.
3. Add quick-note entry points and state-aware active recording controls, then
   conditionally expose Pomodoro and recurring-meeting actions as SPEC-034/035
   become available.
4. Verify cleanup and tray-unavailable fallback, run real Qt/SQLite integration
   tests and full virtualenv suite, and update English/Spanish documentation.

## Integration Boundary Decision

The menu crosses Qt signals, capture lifecycle, persistence, notifications,
and later timers/scheduling. Real Qt/SQLite integration coverage is mandatory;
deterministic doubles replace only platform/hardware or external edges.
