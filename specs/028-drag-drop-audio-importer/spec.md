# SPEC-028: Drag & Drop Audio Importer

Status: Implemented and validated
Owner: Héctor Álvarez López <hector.alvarez@diagroup.com>
Last updated: 2026-09-18

## Product contract
- `MainWindow` accepts one local regular audio file dragged over any part of the
  application. Supported extensions are `.mp3`, `.wav`, `.m4a`, `.flac` and `.ogg`,
  case-insensitively. Directories, remote URLs, multiple files and other formats
  are rejected without opening dialogs or changing application state.
- A translucent overlay identifies the accepted file and is hidden on leave/drop;
  it expands with the window and does not intercept mouse input.
- A valid drop routes directly to the existing import flow: copy to the unique
  `recordings/` filename, persist the SQLite recording, open its recording tab and
  call `start_transcription_with_config`. The status bar reports the file being
  imported and transcribed.
- The existing menu/dialog import remains available and shares the same copy,
  persistence and transcription path. Import failures continue to use the existing
  error dialog and return no record id.

## Scope and boundaries
Validation covers the Qt drag event contract with deterministic MIME data, the
copy/persistence/transcription boundary with a temporary SQLite database, and the
existing dialog import behavior. Network, audio hardware and transcription models
remain outside the test boundary.
