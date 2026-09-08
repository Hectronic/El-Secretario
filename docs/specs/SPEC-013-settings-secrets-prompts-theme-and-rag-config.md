# SPEC-013: Settings, Secrets, Prompts, Theme, And RAG Configuration

Status: Implemented
Owner: TBD
Last updated: 2026-09-07

## Problem

Users need one durable configuration surface for credentials, prompts, theme,
audio/transcription choices, and RAG behavior without exposing secrets by default.

## Scope

- In scope: settings panels, QSettings load/save, secret-field visibility/copy,
  prompts, application theme, audio/STT preferences, and RAG configuration.
- Out of scope: provider request execution, transcription runtime fallback
  (SPEC-002), and RAG indexing/search behavior (SPEC-006).

## User Stories

- As a user, I want my settings to reload after restarting so that configuration is
  durable.
- As a user, I want credentials hidden by default but available to reveal or copy
  intentionally.
- As a user, I want to choose prompts, theme, backend, and RAG options so that the
  application matches my workflow and machine.

## Acceptance Criteria

- Given values have been saved, when Settings reopens with the same QSettings
  store, then credentials, theme, scheduling flags, prompts, and audio/RAG options
  are restored.
- Given a secret field is displayed, when the user has not requested visibility,
  then it uses password presentation; reveal/hide and copy are explicit actions.
- Given Sherpa-ONNX, backend, audio-device, or RAG options are changed, when saved,
  then their settings keys retain the selected values without changing unrelated
  user preferences.

## Architecture Notes

- UI: `src/ui/settings/` contains focused audio, general, prompts, and RAG panels;
  `src/ui/secret_field_widget.py` owns secret interactions.
- Services: `src/ui/styles.py` applies the selected theme and
  `src/rag/runtime_policy.py` consumes platform-safe RAG execution flags.
- Persistence: Qt `QSettings` is the durable settings store; worker runtime
  snapshots are written separately by `src/worker_components/settings.py` and do
  not overwrite user preferences.
- Platform constraints: all panels and QSettings behavior must work on Windows,
  Ubuntu, and macOS; secret fields must not expose values merely because a platform
  has a different native style.

## Test Plan

- Integration/UI: `tests/test_settings.py` uses a temporary real QSettings store to
  cover load/save, secrets, prompts, theme, audio, and RAG values.
- Unit: `tests/ui/settings/`, `tests/ui/test_secret_field_widget.py`, and
  `tests/worker_components/test_settings.py` cover focused panels, secret behavior,
  and non-destructive worker snapshots.
- Manual: verify settings persistence across restart and theme switching on every
  supported desktop platform.

## Documentation

- README: provider tokens and settings entry points are documented.
- Other docs: SPEC-002 and SPEC-006 define runtime consumers of these settings.

## Open Questions

- Should secure OS credential storage replace raw QSettings for provider tokens in a
  future security-focused change?
