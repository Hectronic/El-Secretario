# Implementation Plan: Automatic Audio Compression

Status: Implemented
Last updated: 2026-09-19
Spec: [spec.md](spec.md)

## Phases

### Phase 1: Compression Engine
- Integrate background compression logic inside `src/audio.py`.
- Utilize `pydub` (which wraps `ffmpeg` internally) or fallback to a lightweight subprocess python-native compression routine.
- Target format: Mono `.mp3` at 32kbps or `.opus` at 24kbps.

### Phase 2: Workflow Lifecycle Integration
- Connect to `Recorder.stop()` return output.
- Start a background thread (`QThread` or standard python thread) to execute the compression, so the UI and transcription start remain completely instantaneous and uninterrupted.
- Once compression succeeds, write the compressed file path, update the SQLite records row in `DBManager`, and delete the original `.wav` file.

### Phase 3: STT Validation
- Verify that Whisper, Faster-Whisper, and Sherpa-ONNX backends read and transcribe the compressed files flawlessly.

## Delivered design
- `src/audio.py` provides an atomic MP3 voice encoder, `AudioCompressionJob`, and Qt-notifying `AudioCompressionService`.
- `RecordingTabCoordinator` starts the job as soon as a capture has a SQLite record, while `RecordingWidget` releases the source after transcription completes or fails.
- `RecordsRepository.replace_filename` conditionally swaps the filename so a deleted or changed record cannot be overwritten by a background job.
- The completed-file signal refreshes the active widget source; failures retain and restore its WAV source.

## Validation
- Compression, SQLite swap, Qt service, and full capture lifecycle integration tests pass.
- Shared capture/transcription/persistence coverage passes (`117 passed, 8 subtests passed`).
- Full suite completed successfully with exit code `0`.
