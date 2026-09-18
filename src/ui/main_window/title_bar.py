# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.

"""Custom frameless title bar with native menu integration for El Secretario."""

import os
import sys

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QMenuBar,
    QMenu,
    QApplication,
    QStyle,
    QDialog,
    QVBoxLayout,
    QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QIcon, QAction, QPixmap


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)


class AboutDialog(QDialog):
    """Custom About modal dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About El Secretario")
        self.setFixedSize(450, 250)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)

        # Logo
        logo_label = QLabel()
        logo_path = get_resource_path("resources/logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            pixmap = pixmap.scaledToHeight(80, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pixmap)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)

        # Title
        title_label = QLabel("El Secretario")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Description
        desc_label = QLabel(
            "Intelligent audio transcription and organization tool.\n\n"
            "Version 1.0.0\n"
            "Copyright (C) 2026 Héctor Álvarez López <hector.alvarez@diagroup.com>\n"
            "Licensed under the GNU General Public License v3.0"
        )
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_label)

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)


class TitleBarWidget(QWidget):
    """A custom widget acting as the frameless window title bar and menu container."""

    def __init__(self, parent):
        super().__init__(parent)
        # Store parent explicitly to avoid garbage collection issues
        self.main_window = parent
        self._drag_position = None
        self._is_maximized = False
        
        self.setFixedHeight(35)
        self.setObjectName("CustomTitleBar")
        
        # We handle background color styling dynamically through the main app stylesheet
        # but apply base structure here.
        self.setStyleSheet("""
            QWidget#CustomTitleBar {
                background: palette(window);
                border-bottom: 1px solid palette(mid);
            }
            QPushButton {
                background: transparent;
                border: none;
                padding: 5px;
            }
            QPushButton:hover {
                background: rgba(150, 150, 150, 0.3);
            }
            QPushButton#CloseButton:hover {
                background: #E81123;
                color: white;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(10)

        # 1. Icon
        self.icon_label = QLabel()
        logo_path = get_resource_path("resources/logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            pixmap = pixmap.scaledToHeight(20, Qt.TransformationMode.SmoothTransformation)
            self.icon_label.setPixmap(pixmap)
        layout.addWidget(self.icon_label)

        # 2. Main Menu Bar
        self.menu_bar = QMenuBar(self)
        self.menu_bar.setStyleSheet("""
            QMenuBar {
                background: transparent;
            }
            QMenuBar::item {
                spacing: 3px;
                padding: 4px 8px;
                background: transparent;
            }
            QMenuBar::item:selected {
                background: rgba(150, 150, 150, 0.3);
                border-radius: 4px;
            }
        """)
        self._setup_menus()
        layout.addWidget(self.menu_bar)

        # Spacer to push window controls to the right
        layout.addStretch()

        # 3. Window Control Buttons
        self.btn_tray = QPushButton("📥") # Minimize to tray
        self.btn_tray.setToolTip("Minimize to System Tray")
        self.btn_tray.setFixedSize(40, 35)
        self.btn_tray.clicked.connect(self._minimize_to_tray)
        layout.addWidget(self.btn_tray)

        self.btn_minimize = QPushButton("🗕")
        self.btn_minimize.setFixedSize(40, 35)
        self.btn_minimize.clicked.connect(self._minimize_window)
        layout.addWidget(self.btn_minimize)

        self.btn_maximize = QPushButton("🗖")
        self.btn_maximize.setFixedSize(40, 35)
        self.btn_maximize.clicked.connect(self._toggle_maximize)
        layout.addWidget(self.btn_maximize)

        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("CloseButton")
        self.btn_close.setFixedSize(40, 35)
        self.btn_close.clicked.connect(self._close_window)
        layout.addWidget(self.btn_close)
        
        # Ensure buttons have proper zero-margin placement
        layout.setContentsMargins(10, 0, 0, 0)

    def _setup_menus(self):
        """Sets up File, Edit, and Help menus."""
        # --- File Menu ---
        file_menu = self.menu_bar.addMenu("&File")
        
        import_action = QAction("Import Audio File...", self)
        import_action.triggered.connect(lambda: getattr(self.main_window, "import_audio_file")() if hasattr(self.main_window, "import_audio_file") else None)
        file_menu.addAction(import_action)

        file_menu.addSeparator()

        tools_action = QAction("Tools", self)
        tools_action.triggered.connect(lambda: getattr(self.main_window.central_tabs, "setCurrentIndex")(1) if hasattr(self.main_window, "central_tabs") else None)
        file_menu.addAction(tools_action)

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(lambda: getattr(self.main_window.central_tabs, "setCurrentIndex")(self.main_window.central_tabs.count()-1) if hasattr(self.main_window, "central_tabs") else None)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        exit_action = QAction("Force Exit", self)
        exit_action.triggered.connect(lambda: getattr(self.main_window, "force_quit")() if hasattr(self.main_window, "force_quit") else None)
        file_menu.addAction(exit_action)

        # --- Edit Menu ---
        edit_menu = self.menu_bar.addMenu("&Edit")
        
        clear_chat_action = QAction("Clear Current Chat", self)
        clear_chat_action.triggered.connect(self._clear_active_chat)
        edit_menu.addAction(clear_chat_action)

        # --- Help Menu ---
        help_menu = self.menu_bar.addMenu("&Help")
        
        about_action = QAction("About El Secretario...", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _clear_active_chat(self):
        """Finds the active chat widget if on Chat tab, and clears its session."""
        try:
            if hasattr(self.main_window, "central_tabs") and self.main_window.central_tabs.currentIndex() == 0:
                chat_tab = self.main_window.central_tabs.currentWidget()
                if hasattr(chat_tab, "chat_widget"):
                    chat_tab.chat_widget.start_new_session()
        except Exception:
            pass

    def _show_about_dialog(self):
        """Displays the custom About modal."""
        dlg = AboutDialog(self.main_window)
        dlg.exec()

    # --- Window Actions ---
    def _minimize_window(self):
        self.main_window.showMinimized()

    def _minimize_to_tray(self):
        self.main_window.hide()
        if hasattr(self.main_window, "system_tray_manager") and self.main_window.system_tray_manager:
            self.main_window.system_tray_manager.show_message(
                "El Secretario", "Minimized to system tray. Active and ready!"
            )

    def _toggle_maximize(self):
        if self._is_maximized:
            self.main_window.showNormal()
            self._is_maximized = False
            self.btn_maximize.setText("🗖")
        else:
            self.main_window.showMaximized()
            self._is_maximized = True
            self.btn_maximize.setText("🗗") # Restore icon

    def _close_window(self):
        reply = QMessageBox.question(
            self,
            "Confirm Close",
            "Are you sure you want to close El Secretario completely?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if hasattr(self.main_window, "force_quit"):
                self.main_window.force_quit()
            else:
                self.main_window.close()

    # --- Mouse Event Overrides for Dragging ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Calculate distance between mouse click and window top-left corner
            self._drag_position = event.globalPosition().toPoint() - self.main_window.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_position:
            # Don't drag if maximized
            if not self._is_maximized:
                self.main_window.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
        else:
            super().mouseMoveEvent(event)
            
    def mouseReleaseEvent(self, event):
        self._drag_position = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximize()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)
