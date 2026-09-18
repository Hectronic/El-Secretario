# Implementation Plan: Automatic Audio Compression

Status: Draft
Last updated: 2026-09-17
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
