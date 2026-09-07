# SPEC-003: Diarization And Speaker Management

Status: Implemented
Owner: TBD
Last updated: 2026-09-07

## Problem

Recordings with multiple speakers need readable attribution without making
transcription unreliable on systems without a compatible GPU or diarization
configuration.

## Scope

- In scope: enabling diarization in transcription configuration, preserving speaker
  labels in stored transcriptions, and optionally renaming displayed labels.
- Out of scope: choosing the transcription backend (SPEC-002), recording metadata
  persistence (SPEC-004), and AI summaries.

## User Stories

- As a user, I want to request diarization while transcribing so that different
  speakers are identifiable in the resulting text.
- As a user, I want to rename generic speaker labels so that a transcript is easy
  to read and remains faithful to its recorded content.

## Acceptance Criteria

- Given diarization is enabled, when a transcription is queued or started directly,
  then its worker receives the diarization option and the saved record is marked as
  diarized when the result confirms it.
- Given a transcript contains repeated `SPEAKER_XX` labels, when the user maps a
  label to a name, then every occurrence is replaced; blank or unchanged labels are
  left untouched.
- Given diarization cannot use GPU safely, when the runtime chooses a supported
  fallback, then the configured backend/device policy from SPEC-002 is preserved.

## Architecture Notes

- UI: `src/ui/speaker_dialog.py` collects optional label mappings and
  `src/ui/recording/speaker_actions.py` applies them. `RecordingWidget` exposes the
  compatible recording-detail actions.
- Workers: `src/worker_components/transcription_flow.py` merges diarization tracks
  with segments; runtime/device decisions remain in `src/worker_components/`.
- Persistence: `src/persistence/records.py` stores the `is_diarized` record state.
- Platform constraints: GPU use follows the shared runtime policy; CPU fallback is
  permitted only when configuration or runtime availability requires it.

## Test Plan

- Unit/UI: `tests/ui/recording/test_speaker_actions.py`,
  `tests/ui/test_speaker_dialog.py`, and
  `tests/worker_components/test_transcription_flow.py` cover labels, dialog output,
  and merged speaker segments.
- Integration: `tests/test_summary_task_queue_integration.py` verifies queued
  transcription forwards diarization and persists its result through SQLite with a
  controlled worker boundary.
- Manual: validate a real multi-speaker sample on supported GPU and CPU-only hosts.

## Documentation

- README: diarization prerequisites and Hugging Face access remain documented.
- Other docs: SPEC-002 defines the shared runtime-policy contract.

## Open Questions

- Should speaker names become reusable profile metadata rather than per-recording
  text replacements?
