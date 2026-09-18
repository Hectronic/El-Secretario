# Tasks: Automatic Audio Compression

Status: Draft
Last updated: 2026-09-17

- [ ] T001 Write the background audio compression routine supporting `.mp3` / `.opus` voice profiles inside `src/audio.py`.
- [ ] T002 Implement the non-blocking worker thread to trigger compression as soon as recording stops.
- [ ] T003 Code the SQLite database path update and original WAV file deletion logic.
- [ ] T004 Verify compatibility of compressed formats with STT engines (faster-whisper, sherpa-onnx, openai-whisper).
- [ ] T005 Write unit tests verifying file sizes, database swap transactions, and compression ratios.
