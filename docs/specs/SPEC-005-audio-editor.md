# SPEC-005: Waveform Audio Editor And Safe Retranscription

Status: Implemented
Owner: TBD
Last updated: 2026-05-10

## Problem

Users need to inspect and edit recordings before continuing with transcription, summarization, search, and chat workflows. Edits must preserve recoverability and keep derived text aligned with the edited audio.

## Scope

- In scope: opening a dedicated audio editor tab, rendering waveform lanes, selecting segments, splitting/cutting/reordering chunks, previewing edited audio, saving edits safely, and retranscribing after save.
- Out of scope: destructive editing without backup, multitrack mixing, non-audio metadata editing, and editing chat/summaries directly.

## User Stories

- As a user, I want to open a recording in an audio editor so that I can remove irrelevant sections.
- As a user, I want a visible waveform so that I can choose cut points accurately.
- As a user, I want saves to keep a backup so that I can recover the original file.
- As a user, I want the recording retranscribed after editing so that text, summaries, RAG, and chat context do not refer to stale audio.

## Acceptance Criteria

- Given an existing recording, when the user opens the audio editor, then the editor loads the audio and displays waveform information.
- Given a selected range, when the user cuts or splits it, then the editor updates the chunk list without modifying the source file immediately.
- Given unsaved edits, when the user previews, then playback uses the edited segment order.
- Given the user applies edits for the first time, when the edited audio is written, then a `.orig` backup of the original file is preserved.
- Given edited audio is saved, when the save succeeds, then retranscription is triggered with the configured transcription model and runtime preferences.
- Given a Sherpa-ONNX model is selected but preflight fails, when retranscription would start, then the user sees the preflight error instead of starting an invalid worker.

## Architecture Notes

- UI: `src/ui/audio_editor/widget.py` owns editor interactions; `src/ui/audio_editor/waveform.py` owns waveform rendering and waveform input events.
- Main window: `src/ui/main_window/recording_tabs.py` owns opening editor tabs and integrating them with tab lifecycle.
- Services: audio cutting currently uses `src/audio.py`; future complex editing should move into `src/services/audio_editing.py`.
- Persistence: `src/database.py` updates record duration/transcription metadata after successful edit/transcription.
- Workers/integrations: `src/worker_components/transcriber_thread.py` performs retranscription and must respect configured backend/device/compute policy.
- Platform constraints: preserve Windows/Ubuntu compatibility and keep CUDA cleanup behavior in transcription paths.

## Test Plan

- Unit: waveform selection, chunk boundaries, split/cut/reorder behavior.
- Integration: editor tab opens from a recording and edited audio triggers retranscription.
- UI: basic widget state transitions for load, edit, preview, and apply.
- Manual: verify real audio playback and waveform rendering on Ubuntu and Windows.

## Documentation

- README: audio editing feature listed in English, Spanish, and Asturian variants.
- Architecture: registered in `docs/ARCHITECTURE.md`.

## Open Questions

- Should the old marker-based trim controls in `RecordingWidget` be deprecated now that the waveform editor exists?
- Should audio-edit operations become an explicit service with a non-Qt command model for easier testing?
