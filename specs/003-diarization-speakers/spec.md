# SPEC-003: Diarization And Speaker Management

Status: Implemented
Owner: TBD
Last updated: 2026-09-26

## Problem

Recordings with multiple speakers need readable attribution without making
transcription unreliable on systems without a compatible GPU or diarization
configuration.

## Scope

- In scope: enabling diarization in transcription configuration, preserving speaker
  labels in stored transcriptions, optionally renaming displayed labels, and
  keeping long-audio diarization responsive and efficient.
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
- Given CUDA is available and CPU was not explicitly requested, diarization
  attempts CUDA even when free VRAM is limited, starts with conservative adaptive
  batches, and retries on CPU only after a real CUDA runtime failure.
- Given a transcript has many segments and speaker turns, speaker attribution
  indexes diarization intervals once rather than rescanning all turns per segment.
- Given pyannote advances from segmentation to counting, embeddings, clustering,
  and reconstruction, the UI reports each stage independently so the last
  segmentation counter cannot appear as a frozen overall state.

## Architecture Notes

- UI: `src/ui/speaker_dialog.py` collects optional label mappings and
  `src/ui/recording/speaker_actions.py` applies them. `RecordingWidget` exposes the
  compatible recording-detail actions.
- Workers: `src/worker_components/transcription_flow.py` merges diarization tracks
  with segments through a prefix-maximum interval index; runtime/device decisions
  remain in `src/worker_components/`. CUDA batch sizes scale with free VRAM after
  model loading, while CPU uses pyannote's conservative batch size of one. Worker
  progress maps pyannote's segmentation, speaker counting, embedding, clustering,
  and reconstruction callbacks to distinct status updates.
- Persistence: `src/persistence/records.py` stores the `is_diarized` record state.
- Platform constraints: GPU use follows the shared runtime policy; CPU fallback is
  permitted only when configuration or runtime availability requires it.

## Test Plan

- Unit/UI: `tests/ui/recording/test_speaker_actions.py`,
  `tests/ui/test_speaker_dialog.py`, and
  `tests/worker_components/test_transcription_flow.py` cover labels, dialog output,
  and indexed speaker alignment. `tests/worker_components/test_runtime.py` covers
  CUDA preference and adaptive batch sizing.
- Integration: `tests/test_summary_task_queue_integration.py` verifies queued
  transcription forwards diarization and persists its result through SQLite with a
  controlled worker boundary. `tests/worker/test_worker_integration.py` verifies
  the real Qt worker reports long-audio diarization progress with GPU batches.
- Manual: validate a real multi-speaker sample on supported GPU and CPU-only hosts.

## Documentation

- README: diarization prerequisites and Hugging Face access remain documented.
- Other docs: SPEC-002 defines the shared runtime-policy contract.

## Open Questions

- Should speaker names become reusable profile metadata rather than per-recording
  text replacements?
