# Implementation Plan: Recurring Meetings, Prepared Metadata, And Reminders

**Branch**: `035-recurring-meetings` | **Status**: Proposed

## Delivery Outline

1. Define versioned recurrence data and occurrence repositories with migration
   and idempotent identity rules.
2. Implement and unit-test a time-zone-aware scheduling service with injectable
   clock and reminder ports before adding Qt presentation.
3. Add template/occurrence editing and calendar display with preview/validation.
4. Connect reminder actions to the existing recording preparation lifecycle and
   preserve occurrence provenance on saved recordings.
5. Add real-SQLite/real-Qt integration coverage, full-suite validation, and
   bilingual documentation.

## Integration Boundary Decision

This feature crosses scheduling lifecycle, persistence, notifications, UI
signals, calendar selection, and recording preparation. Integration tests are
mandatory and must use real application boundaries apart from external edges.
