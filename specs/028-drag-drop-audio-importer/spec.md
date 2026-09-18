# SPEC-028: Drag & Drop Audio Importer

Status: Draft
Owner: Héctor Álvarez López <hector.alvarez@diagroup.com>
Last updated: 2026-09-17

## Problem
Currently, importing a recording requires multiple clicks: opening the Tools or File menu, triggering the "Import Audio File" dialogue, and navigating the system directories to select a file. This traditional flow is tedious for users who frequently handle audio files generated on external recorders or received via messaging clients.

## Proposal
Implement direct, seamless Drag & Drop capabilities across the entire `MainWindow` frame. Users can simply drag an audio file from their operating system's file browser and drop it onto any section of El Secretario to trigger an instant import.

### Key Highlights
- **Universal Drag & Drop:** Override Drag-and-Drop events on `MainWindow` so that dragging files into any part of the active interface is recognized.
- **Audio Format Validation:** Intercept MIME types during dragging to only accept supported audio formats (e.g. `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`). Reject any unsupported formats or directories visually.
- **Instant Flow Triggering:** Once a valid file is dropped, the app copies the file into the user space recordings folder, initiates a new database recording entry, and enqueues it directly into the transcription worker thread.

## User Scenarios & Testing
- **Scenario:** The user drags `interview.mp3` from their Nautilus file browser over El Secretario. The window displays a subtle overlay saying "Drop to import interview.mp3". The user releases the mouse. The app switches to the processing queue showing "Transcribing: interview.mp3" instantly.
- **Testing:** Add PyQt-QtBot tests simulating drop events with mock MIMEDict files containing both valid and invalid extensions, asserting routing outputs and file copy checks.
