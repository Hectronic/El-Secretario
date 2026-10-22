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

## Windows CI follow-up (2026-10-22, REQ-031.1)

CI run 39798480934 failed only on Windows: the real Qt/SQLite capture lifecycle test observed the WAV retained after the media source was detached. Windows can release the FFmpeg handle asynchronously. The background worker now retries PermissionError up to 10 times with 100 ms between attempts; the Qt thread stays free. Persistent failures still retain the original WAV and valid MP3 reference.

No owner changes or file moves. Unit regression covers transient and persistent sharing locks. Existing `tests/integration/test_recording_compression_lifecycle.py` proves the real capture → Qt source release → worker → SQLite filename swap → original-file removal contract; `test_audio_compression_service.py` proves the real completion signal follows persistence and cleanup. Native Windows CI will verify its actual backend.

Focused units (30 passed, including Settings):

```bash
QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest tests/test_audio_compression.py tests/ui/settings -q
```

Focused integration (5 passed, including Settings):

```bash
QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest tests/integration/test_recording_compression_lifecycle.py tests/integration/test_audio_compression_service.py tests/integration/test_settings_experience.py tests/integration/test_recording_player_state.py -q
```

Full Linux/offscreen suite: 1037 passed, 1 skipped (system tray unavailable), 11 subtests passed in 129.35 seconds; command `QT_QPA_PLATFORM=offscreen PYTHONUNBUFFERED=1 ./.venv/bin/python -m pytest -q`. Native Windows validation is tracked in [PR #67 checks](https://github.com/Hectronic/El-Secretario/pull/67/checks).
