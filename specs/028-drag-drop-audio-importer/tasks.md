# Tasks: Drag & Drop Audio Importer

Status: Draft
Last updated: 2026-09-17

- [ ] T001 Configure main window frames to accept drag-and-drop actions.
- [ ] T002 Program the MIME-type filtering inside `dragEnterEvent` supporting `.mp3`, `.wav`, `.m4a`, `.flac`, `.ogg`.
- [ ] T003 Code `dropEvent` routing to extract paths and trigger the import flow.
- [ ] T004 Implement an elegant drag visual overlay/glasspane on `MainWindow`.
- [ ] T005 Write unit tests simulating QMimeData drops with varying file profiles and extensions.
