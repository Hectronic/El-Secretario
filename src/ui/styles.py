# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QSettings
try:
    import darkdetect
except ImportError:
    darkdetect = None

# Define constants for backward compatibility (they will be empty as we move to global sheet)
# Or we can keep them for specific overrides if needed, but primarily we want the global sheet to rule.
LIST_WIDGET_STYLE = ""
TEXT_EDIT_STYLE = ""
# Primary buttons might still need specific colors if not handled by generic selector
BUTTON_PRIMARY_STYLE = """
    QPushButton {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        padding: 5px 15px;
        border-radius: 4px;
    }
"""
BUTTON_DANGER_STYLE = """
    QPushButton {
        color: #f44336;
        font-weight: bold;
        background: transparent;
        border: 1px solid #f44336;
        padding: 5px 15px;
        border-radius: 4px;
    }
"""
NEW_CHAT_BUTTON_STYLE = """
    QPushButton {
        background-color: #4CAF50; 
        color: white; 
        font-weight: bold; 
        padding: 8px;
        border-radius: 4px;
    }
"""

DARK_STYLESHEET = """
    QWidget {
        background-color: #2b2b2b;
        color: #eeeeee;
    }
    QListWidget {
        border: none;
        background-color: #2b2b2b;
        color: #eeeeee;
    }
    QListWidget::item {
        padding: 5px;
        border-bottom: 1px solid #3a3a3a;
    }
    QListWidget::item:hover {
        background-color: #3a3a3a;
    }
    QListWidget::item:selected {
        background-color: #4a4a4a;
    }
    QLineEdit, QTextEdit, QPlainTextEdit {
        background-color: #333333;
        color: #eeeeee;
        border: 1px solid #555555;
        border-radius: 3px;
        padding: 5px;
    }
    QLabel {
        color: #eeeeee;
    }
    QTabWidget::pane {
        border: 1px solid #444444;
    }
    QTabBar::tab {
        background: #333333;
        color: #bbbbbb;
        padding: 8px 12px;
        border: 1px solid #444444;
        border-bottom-color: #444444;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected {
        background: #4a4a4a;
        color: #ffffff;
        border-bottom-color: #4a4a4a; 
    }
    QSplitter::handle {
        background-color: #444444;
    }
    QCalendarWidget QWidget {
        alternate-background-color: #4a4a4a; 
    }
    QMenu {
        background-color: #2b2b2b;
        border: 1px solid #555555;
    }
    QMenu::item {
        padding: 5px 20px;
    }
    QMenu::item:selected {
        background-color: #4a4a4a;
    }
    QListWidget[class="embedded-list"] {
        margin: 0;
        padding: 0;
        border: 1px solid #444444;
    }
    QLabel#record_title {
        color: #eeeeee;
    }
    QLabel#record_details {
        color: #aaaaaa;
    }
"""

LIGHT_STYLESHEET = """
    QWidget {
        background-color: #f5f5f5;
        color: #333333;
    }
    QListWidget {
        border: none;
        background-color: #f5f5f5;
        color: #333333;
        font-size: 14px;
    }
    QListWidget::item {
        padding: 5px;
        border-bottom: 1px solid #e0e0e0;
    }
    QListWidget::item:hover {
        background-color: #e0e0e0;
    }
    QListWidget::item:selected {
        background-color: #d0d0d0;
    }
    QLineEdit, QTextEdit, QPlainTextEdit {
        background-color: #ffffff;
        color: #333333;
        border: 1px solid #cccccc;
        border-radius: 3px;
        padding: 5px;
    }
    QLabel {
        color: #333333;
    }
    QTabWidget::pane {
        border: 1px solid #cccccc;
    }
    QTabBar::tab {
        background: #e0e0e0;
        color: #555555;
        padding: 8px 12px;
        border: 1px solid #cccccc;
        border-bottom-color: #cccccc;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected {
        background: #ffffff;
        color: #000000;
        border-bottom-color: #ffffff;
    }
    QSplitter::handle {
        background-color: #cccccc;
    }
    QMenu {
        background-color: #ffffff;
        border: 1px solid #cccccc;
    }
    QMenu::item {
        padding: 5px 20px;
    }
    QMenu::item:selected {
        background-color: #e0e0e0;
    }
    QListWidget[class="embedded-list"] {
        margin: 0;
        padding: 0;
        border: 1px solid #cccccc;
    }
    QCalendarWidget QWidget {
        alternate-background-color: #e0e0e0;
        background-color: #ffffff;
        color: #333333;
    }
    QCalendarWidget QToolButton {
        color: #333333;
        font-weight: bold;
        icon-size: 24px;
    }
    QCalendarWidget QMenu {
        background-color: #ffffff;
        color: #333333;
    }
    QCalendarWidget QSpinBox {
        background-color: #ffffff;
        color: #333333;
        selection-background-color: #d0d0d0;
        selection-color: #000000;
    }
    QCalendarWidget QAbstractItemView:enabled {
        background-color: #ffffff;
        color: #333333;
        selection-background-color: #2196F3;
        selection-color: #ffffff;
    }
    QCalendarWidget QAbstractItemView:disabled {
        color: #999999;
    }
    QComboBox {
        background-color: #ffffff;
        color: #333333;
        border: 1px solid #cccccc;
        border-radius: 3px;
        padding: 4px;
    }
    QComboBox::drop-down {
        border: none;
        background: transparent;
    }
    QToolTip {
        background-color: #ffffff;
        color: #333333;
        border: 1px solid #cccccc;
    }
    QLabel#record_title {
        color: #333333;
    }
    QLabel#record_details {
        color: #666666;
    }
"""

def apply_theme(theme_name=None):
    """
    Apply the specified theme to the global application instance.
    theme_name: "Light", "Dark", or "System".
    If None, reads from QSettings.
    """
    app = QApplication.instance()
    if not app:
        return

    settings = QSettings("Hectronic", "Secretario")
    
    if not theme_name:
        theme_name = settings.value("app_theme", "System")
        
    # System Detection
    if theme_name == "System":
        # simple check using a library if we had one, or fallback
        # Ideally we'd use: 
        # is_dark = app.styleHints().colorScheme() == Qt.ColorScheme.Dark
        # But that's Qt 6.5+. Let's assume user might have older Qt or it's reliable enough.
        # Fallback to darkdetect if available, else Dark (safe default).
        try:
            is_dark = darkdetect.isDark()
        except:
            is_dark = True # Default to Dark
    elif theme_name == "Dark":
        is_dark = True
    else: # Light
        is_dark = False
        
    if is_dark:
        app.setStyleSheet(DARK_STYLESHEET)
    else:
        app.setStyleSheet(LIGHT_STYLESHEET)
