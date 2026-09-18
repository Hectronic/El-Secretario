# Implementation Plan: Drag & Drop Audio Importer

Status: Draft
Last updated: 2026-09-17
Spec: [spec.md](spec.md)

## Phases

### Phase 1: Event Overrides
- Configure `MainWindow` and central layouts with `setAcceptDrops(True)`.
- Implement `dragEnterEvent` to extract file URLs and filter by supported extensions.
- Provide interactive drag feedback (e.g., cursor shape changes or temporary styled glasspane overlay).

### Phase 2: Drop Processing
- Implement `dropEvent` to capture local absolute file paths.
- Call the central `MainWindow.import_audio_file` setup routine directly, passing the path.
- Trigger transition to the central tab layout so the user can observe processing progress immediately.

### Phase 3: Robustness and Edge Cases
- Ensure dragging directories is rejected.
- Provide descriptive user warning toasts if the file copy or validation fails.
