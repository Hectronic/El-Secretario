# Implementation Plan: Custom Title Bar and Menus

Status: Implemented
Last updated: 2026-09-15
Spec: [spec.md](spec.md)

## Phases

### Phase 1: Custom Title Bar Widget Creation
- Create the `TitleBarWidget` class under `src/ui/main_window/title_bar.py`.
- Add icons for minimize, minimize-to-tray, maximize, restore, and close.
- Implement dragging mathematical models within Qt mouse overrides.
- Apply stylesheet bindings so that title bar backgrounds and text colors adjust instantly when Light, Dark, or SNES themes are applied.

### Phase 2: Menu Bar Integration
- Embed a `QMenuBar` on the left side of the `TitleBarWidget`.
- Create menus for `File`, `Edit`, and `Help`.
- Link actions:
  - `File` -> `Import Audio File` to trigger `import_audio_file`.
  - `File` -> `Tools` to open the tools tab.
  - `File` -> `Settings` to open the settings tab.
  - `File` -> `Force Exit` to run `force_quit()`.
  - `Help` -> `About` to display a styled About dialog.

### Phase 3: MainWindow Adaptation
- Update `MainWindow.__init__` to apply the frameless window flags (`Qt.WindowType.FramelessWindowHint`).
- Set the layout to include our `TitleBarWidget` pinned at the very top.
- Enable smooth mouse-based window resizing options along borders if necessary (optional but highly recommended).

### Phase 4: Unit & Integration Testing
- Write comprehensive test suites under `tests/ui/main_window/test_title_bar.py`.
- Verify standard minimize, maximize, and minimize-to-tray operations.
- Ensure that the application menu successfully opens sub-windows and tabs.
