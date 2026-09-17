# SPEC-026: Custom Window Title Bar and Native Menus

Status: Implemented
Owner: Héctor Álvarez López <hector.alvarez@diagroup.com>
Last updated: 2026-09-15

## Problem

Standard operating system window title bars look dated, vary wildly across platforms (Windows, Ubuntu, macOS), and do not align with the modern, customizable visual identity (Light, Dark, SNES themes) of El Secretario. Additionally:
- Users want a direct, explicit button to **Minimize to the System Tray** directly on the title bar (rather than standard minimize which minimizes to the OS taskbar).
- The application currently lacks a traditional main menu bar (`File`, `Edit`, `Help`) which is standard for desktop applications, making features like "About the App" or "Keyboard Shortcuts" difficult to discover.

## Scope

- **In scope:**
  - Making the main application window frameless (`Qt.WindowType.FramelessWindowHint`) and designing a custom, highly polished, theme-adaptive `TitleBarWidget`.
  - Custom title bar buttons:
    - **Minimize to Taskbar** (standard hide).
    - **Minimize to System Tray** (hides window, keeps active in tray).
    - **Maximize / Restore** (toggles fullscreen/maximized state).
    - **Close** (standard exit or minimize to tray depending on settings).
  - Window dragging capabilities (handling mouse press and move events on the title bar widget).
  - Integrating a sleek, modern Menu Bar directly on the left side of the title bar or immediately below it:
    - **File:** Import Audio File, Tools Tab, Settings Panel, Force Exit.
    - **Edit:** Clear Current Chat, Toggle Theme.
    - **Help:** View Documentation, Architecture Guide, About El Secretario.
  - A custom-branded "About El Secretario" dialog with authorship, versioning, and license details.
- **Out of scope:**
  - Rewriting platform-specific window managers (we rely on standard Qt frameless window window-moving arithmetic).

## User Stories

- As a user, I want the window title bar to look modern and perfectly match the selected theme (such as Dark or SNES) so the app looks unified.
- As a user, I want to click a dedicated button on the title bar to minimize the app straight to the system tray so that my taskbar stays completely uncluttered.
- As a user, I want a standard menu bar at the top of the app to easily access main tools, settings, documentation, and the "About" dialog.

## Acceptance Criteria

- **Custom Styling:**
  - Launching the application shows a unified top title bar styled according to the current active theme (Light, Dark, or SNES).
- **Drag and Resize:**
  - Clicking and dragging any empty part of the custom title bar moves the window smoothly.
  - Double-clicking the title bar toggles between Maximized and Restored sizes.
- **Minimize to Tray Button:**
  - Clicking the new "Minimize to Tray" icon (e.g. an arrow pointing down into a tray box, placed next to standard minimize) instantly hides the MainWindow and updates the System Tray icon status.
- **Menu Bar Integration:**
  - Selecting options from the `File`, `Edit`, or `Help` menu triggers their respective actions perfectly.
  - Clicking `Help` -> `About` launches a custom branded modal dialog with app info.

## Architecture & Implementation Notes

### 1. Frameless Window Setup
In `src/ui/main_window/__init__.py`:
```python
self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowSystemMenuHint | Qt.WindowType.WindowMinMaxButtonsHint)
```

### 2. Custom Title Bar Widget (`src/ui/main_window/title_bar.py`)
- Standard `QWidget` containing:
  - An application icon and Title Label.
  - An integrated `QMenuBar` styled with CSS to blend into the title bar.
  - A spacer.
  - Action buttons: Minimize, Minimize to Tray, Maximize/Restore, Close.
- Drag arithmetic:
  - Override `mousePressEvent` and `mouseMoveEvent` to track mouse offsets and move the main window:
    ```python
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_position:
            self.window().move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
    ```

### 3. Minimize to System Tray Logic
- The button is connected directly to a MainWindow slot:
  ```python
  def minimize_to_tray(self):
      self.hide()
      if hasattr(self, "system_tray_manager"):
          self.system_tray_manager.show_message(
              "El Secretario", "Minimized to system tray. Active and ready!"
          )
  ```

## Test Plan

- **Unit Tests:**
  - Verify `TitleBarWidget` instantiation and alignment.
  - Verify that window state toggles correctly (Maximized -> Normal) when double-clicking the title bar.
- **Integration Tests:**
  - Verify the custom title bar buttons trigger correct window events (`showMinimized`, `hide`, `close`).
  - Verify the "Minimize to Tray" button successfully calls the tray manager and hides the main window.
- **Manual Verification:**
  - Check window movement stability on Windows, Ubuntu (offscreen and native), and macOS.
  - Verify that menu bar triggers options (e.g. opens settings tab, imports file).
