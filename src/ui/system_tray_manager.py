import logging
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtGui import QIcon, QAction, QPainter, QColor
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

class SystemTrayManager(QObject):
    """Global manager for the application's system tray icon."""

    show_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.app = QApplication.instance()
        self._tray_icon = None
        self._menu = None
        self._is_recording = False

        self._init_tray_icon()

    def _init_tray_icon(self):
        if self.app:
            self.app.setQuitOnLastWindowClosed(False)

        self._menu = QMenu()
        
        # Show/Hide Action
        self.toggle_window_action = QAction("Show El Secretario", self)
        self.toggle_window_action.triggered.connect(self._toggle_main_window)
        self._menu.addAction(self.toggle_window_action)

        self._menu.addSeparator()

        # Recording Actions (hidden by default)
        self.pause_recording_action = QAction("Pause Recording", self)
        self.stop_recording_action = QAction("Stop and Save Recording", self)
        self.cancel_recording_action = QAction("Cancel Recording", self)
        
        self.pause_recording_action.setVisible(False)
        self.stop_recording_action.setVisible(False)
        self.cancel_recording_action.setVisible(False)

        self._menu.addAction(self.pause_recording_action)
        self._menu.addAction(self.stop_recording_action)
        self._menu.addAction(self.cancel_recording_action)

        self._menu.addSeparator()

        # Quit Action
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._on_quit_triggered)
        self._menu.addAction(quit_action)

        if not QSystemTrayIcon.isSystemTrayAvailable():
            logging.warning("System tray is not available on this platform.")
            return

        self._tray_icon = QSystemTrayIcon(self)
        self._update_icon()

        self._tray_icon.setContextMenu(self._menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        
        self._tray_icon.show()

    def _update_icon(self):
        if not self._tray_icon:
            return
            
        base_icon = self.main_window.windowIcon()
        if base_icon.isNull() and self.app:
            base_icon = self.app.windowIcon()

        if self._is_recording:
            # Draw a red circle on the bottom right corner
            pixmap = base_icon.pixmap(64, 64)
            if not pixmap.isNull():
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setBrush(QColor("red"))
                painter.setPen(Qt.PenStyle.NoPen)
                # Draw a circle in the bottom right
                radius = 12
                painter.drawEllipse(pixmap.width() - radius * 2, pixmap.height() - radius * 2, radius * 2, radius * 2)
                painter.end()
                icon = QIcon(pixmap)
                self._tray_icon.setIcon(icon)
            else:
                self._tray_icon.setIcon(base_icon)
            self._tray_icon.setToolTip("El Secretario - Recording in Progress")
        else:
            self._tray_icon.setIcon(base_icon)
            self._tray_icon.setToolTip("El Secretario")

    def set_recording_state(self, is_recording: bool):
        if self._is_recording != is_recording:
            self._is_recording = is_recording
            self._update_icon()

    def show_message(self, title, message):
        if self._tray_icon:
            self._tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information)

    def bind_recording_actions(self, stop_callback, pause_callback, cancel_callback):
        self._disconnect_all(self.pause_recording_action)
        self._disconnect_all(self.stop_recording_action)
        self._disconnect_all(self.cancel_recording_action)
        
        self.pause_recording_action.triggered.connect(pause_callback)
        self.stop_recording_action.triggered.connect(stop_callback)
        self.cancel_recording_action.triggered.connect(cancel_callback)
        
        self.pause_recording_action.setVisible(True)
        self.stop_recording_action.setVisible(True)
        self.cancel_recording_action.setVisible(True)

    def unbind_recording_actions(self):
        self.pause_recording_action.setVisible(False)
        self.stop_recording_action.setVisible(False)
        self.cancel_recording_action.setVisible(False)
        self._disconnect_all(self.pause_recording_action)
        self._disconnect_all(self.stop_recording_action)
        self._disconnect_all(self.cancel_recording_action)

    def _disconnect_all(self, action):
        try:
            action.triggered.disconnect()
        except TypeError:
            pass

    def set_recording_tooltip(self, text):
        if self._tray_icon:
            self._tray_icon.setToolTip(text)

    def set_recording_paused(self, paused):
        self.pause_recording_action.setText("Resume Recording" if paused else "Pause Recording")

    def _toggle_main_window(self):
        if self.main_window.isVisible():
            self.main_window.hide()
            self.toggle_window_action.setText("Show El Secretario")
        else:
            self.main_window.showNormal()
            self.main_window.activateWindow()
            self.main_window.raise_()
            self.toggle_window_action.setText("Hide El Secretario")

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_main_window()

    def _on_quit_triggered(self):
        self.quit_requested.emit()
        self.cleanup()

    def cleanup(self):
        if self._tray_icon:
            self._tray_icon.hide()
            self._tray_icon.deleteLater()
            self._tray_icon = None
