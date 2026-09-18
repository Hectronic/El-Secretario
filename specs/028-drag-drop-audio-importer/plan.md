# Implementation Plan: Drag & Drop Audio Importer

Status: Implemented and validated
Last updated: 2026-09-18
Spec: [spec.md](spec.md)

- Add pure MIME/path validation helpers under `src/ui/main_window/drag_drop.py`.
- Add `MainWindow` drag-enter, move, leave and drop handlers with an expanding
  feedback overlay.
- Refactor `SetupActionsCoordinator` so dialog and drop imports share
  `import_audio_path`, preserving unique filenames, SQLite persistence and the
  transcription start call.
- Keep the recording waveform from SPEC-027 horizontally expanding to the
  available width while retaining its compact/regular heights.
- Validate unit, UI and integration contracts in offscreen Qt mode.

## Validation results (2026-09-18)
- Focused SPEC-027/028 tests: 23 passed.
- Integration import test uses temporary SQLite and filesystem copy assertions.
