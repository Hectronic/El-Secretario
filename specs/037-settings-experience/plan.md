# Implementation Plan: Intuitive Settings With Full Control

**Branch**: `037-settings-experience` | **Status**: Implemented

## Delivery Outline

1. Inventory the existing Settings controls, QSettings keys, defaults, validators,
   runtime consumers, and effective-when semantics; add characterization tests.
2. Define canonical category and search descriptors, Basic/Advanced disclosure,
   and save/apply status without duplicating editable controls.
3. Move controls incrementally into focused `src/ui/settings/` views while keeping
   `SettingsWidget` signals and stored keys compatible.
4. Add staged edit, validation, reset, and navigation safeguards; verify secrets
   and explicit RAG actions retain their safety contracts.
5. Run focused UI/settings and consumer tests, real QSettings/Qt integration tests,
   then the full virtualenv suite. Update README and README_ES.

## Integration Boundary Decision

This redesign crosses UI/signals, QSettings persistence, runtime consumers,
and restart behavior. It requires real Qt/QSettings integration coverage, plus
focused unit tests before any behavior-sensitive refactor.

## Delivered

- Catalog and inventory cover legacy setting keys, defaults, validation,
  consumers, and apply timing across seven settings categories.
- The Settings shell now stages edits, searches and opens controls, validates and
  saves changed fields, supports per-field/category reset, and guards navigation.
- Pomodoro global preferences now live under Automation & notifications; its
  runtime reads the persisted interval preferences.
- README variants and Spec Kit registry updated. Focused verification: 38 passed.
  Full suite: 1002 passed, 1 skipped because the system tray is unavailable,
  and 11 subtests passed.
