# Tasks: Automatic Audio Compression

Status: Implemented
Last updated: 2026-09-19

- [x] T001 Write the background audio compression routine supporting `.mp3` / `.opus` voice profiles inside `src/audio.py`.
- [x] T002 Implement the non-blocking worker thread to trigger compression as soon as recording stops.
- [x] T003 Code the SQLite database path update and original WAV file deletion logic.
- [x] T004 Verify compatibility of compressed formats with STT engines (faster-whisper, sherpa-onnx, openai-whisper).
- [x] T005 Write unit tests verifying file sizes, database swap transactions, and compression ratios.


STT compatibility is validated at the shared local-audio boundary: generated MP3 files are opened through `soundfile` and `Recorder.get_duration`, the same duration-probing path used before backend selection. External model inference remains covered by the existing provider suites.
