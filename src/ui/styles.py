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
    QPushButton[class="calendar-primary-btn"] {
        background-color: #1f6fd5;
        color: #ffffff;
        border: 1px solid #3a83e2;
        border-radius: 10px;
        font-weight: 700;
        padding: 8px 14px;
    }
    QPushButton[class="calendar-primary-btn"]:hover {
        background-color: #2e7fe4;
    }
    QPushButton[class="calendar-primary-btn"]:pressed {
        background-color: #1659aa;
    }
    QPushButton[class="calendar-nav-btn"] {
        background-color: #343a45;
        color: #e8eef7;
        border: 1px solid #4a5463;
        border-radius: 10px;
        font-weight: 600;
        padding: 7px 12px;
    }
    QPushButton[class="calendar-nav-btn"]:hover {
        background-color: #3d4654;
        border-color: #5f6b7f;
    }
    QPushButton[class="calendar-nav-btn"]:pressed {
        background-color: #2c323c;
    }
    QPushButton[class="record-fav-btn"] {
        border: 1px solid transparent;
        border-radius: 13px;
        color: #8d96a4;
        font-size: 16px;
        padding: 0;
        background-color: transparent;
    }
    QPushButton[class="record-fav-btn"]:checked {
        color: #ffc107;
    }
    QPushButton[class="record-fav-btn"]:hover {
        background-color: #3b434f;
    }
    QPushButton[class="record-fav-btn"]:pressed {
        background-color: #313843;
    }
    QPushButton[class="record-del-btn"] {
        border: 1px solid #a85959;
        border-radius: 13px;
        color: #de6a6a;
        font-size: 13px;
        padding: 0;
        background-color: transparent;
    }
    QPushButton[class="record-del-btn"]:hover {
        background-color: #5a2f2f;
        border-color: #c16f6f;
    }
    QPushButton[class="record-del-btn"]:pressed {
        background-color: #4a2626;
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
    TaskRowWidget[completed="true"] {
        background-color: rgba(76, 175, 80, 0.1);
        border-radius: 5px;
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
    QPushButton[class="calendar-primary-btn"] {
        background-color: #1f6fd5;
        color: #ffffff;
        border: 1px solid #1b5fb3;
        border-radius: 10px;
        font-weight: 700;
        padding: 8px 14px;
    }
    QPushButton[class="calendar-primary-btn"]:hover {
        background-color: #2b7de2;
    }
    QPushButton[class="calendar-primary-btn"]:pressed {
        background-color: #195db6;
    }
    QPushButton[class="calendar-nav-btn"] {
        background-color: #ffffff;
        color: #2b3b52;
        border: 1px solid #c6d2e2;
        border-radius: 10px;
        font-weight: 600;
        padding: 7px 12px;
    }
    QPushButton[class="calendar-nav-btn"]:hover {
        background-color: #eef4fb;
        border-color: #a9bfd9;
    }
    QPushButton[class="calendar-nav-btn"]:pressed {
        background-color: #dfeaf8;
    }
    QPushButton[class="record-fav-btn"] {
        border: 1px solid transparent;
        border-radius: 13px;
        color: #7a8596;
        font-size: 16px;
        padding: 0;
        background-color: transparent;
    }
    QPushButton[class="record-fav-btn"]:checked {
        color: #c38b00;
    }
    QPushButton[class="record-fav-btn"]:hover {
        background-color: #f1f5fb;
    }
    QPushButton[class="record-fav-btn"]:pressed {
        background-color: #e4ebf6;
    }
    QPushButton[class="record-del-btn"] {
        border: 1px solid #e0b2b2;
        border-radius: 13px;
        color: #c75a5a;
        font-size: 13px;
        padding: 0;
        background-color: transparent;
    }
    QPushButton[class="record-del-btn"]:hover {
        background-color: #fdeeee;
        border-color: #d98989;
    }
    QPushButton[class="record-del-btn"]:pressed {
        background-color: #f9dddd;
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
    TaskRowWidget[completed="true"] {
        background-color: rgba(76, 175, 80, 0.05);
        border-radius: 5px;
    }
"""

SNES_STYLESHEET = """
    QWidget {
        background-color: #D1D1D1;
        color: #333333;
        font-family: "Segoe UI", sans-serif;
    }
    QListWidget {
        border: 2px solid #A1A1A1;
        background-color: #E1E1E1;
        color: #333333;
        border-radius: 5px;
    }
    QListWidget::item {
        padding: 8px;
        border-bottom: 1px solid #A1A1A1;
    }
    QListWidget::item:hover {
        background-color: #BFAEE3;
    }
    QListWidget::item:selected {
        background-color: #7B59AB;
        color: white;
    }
    QLineEdit, QTextEdit, QPlainTextEdit {
        background-color: #FFFFFF;
        color: #333333;
        border: 2px solid #7B59AB;
        border-radius: 5px;
        padding: 5px;
    }
    QLabel {
        color: #333333;
    }
    QTabWidget::pane {
        border: 2px solid #7B59AB;
        border-radius: 5px;
        background-color: #D1D1D1;
    }
    QTabBar::tab {
        background: #A1A1A1;
        color: #333333;
        padding: 10px 15px;
        border: 2px solid #7B59AB;
        border-bottom: none;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        margin-right: 2px;
    }
    QTabBar::tab:selected {
        background: #7B59AB;
        color: #FFFFFF;
    }
    QSplitter::handle {
        background-color: #7B59AB;
    }
    QMenu {
        background-color: #D1D1D1;
        border: 2px solid #7B59AB;
    }
    QMenu::item:selected {
        background-color: #7B59AB;
        color: white;
    }
    QPushButton[class="calendar-primary-btn"] {
        background-color: #00A651; /* SNES Green */
        color: #ffffff;
        border: 2px solid #007B3E;
        border-radius: 12px;
        font-weight: 700;
        padding: 8px 14px;
    }
    QPushButton[class="calendar-primary-btn"]:hover {
        background-color: #00C864;
    }
    QPushButton[class="calendar-nav-btn"] {
        background-color: #F2B807; /* SNES Yellow */
        color: #333333;
        border: 2px solid #C69206;
        border-radius: 12px;
        font-weight: 600;
        padding: 7px 12px;
    }
    QPushButton[class="calendar-nav-btn"]:hover {
        background-color: #FFD54F;
    }
    QPushButton[class="record-fav-btn"] {
        color: #0072BC; /* SNES Blue */
        font-size: 18px;
        background-color: transparent;
        border: none;
    }
    QPushButton[class="record-fav-btn"]:checked {
        color: #F2B807; /* SNES Yellow */
    }
    QPushButton[class="record-del-btn"] {
        color: #E60012; /* SNES Red */
        font-size: 14px;
        border: 2px solid #E60012;
        border-radius: 13px;
        background-color: transparent;
    }
    QPushButton[class="record-del-btn"]:hover {
        background-color: #FFCDD2;
    }
    QProgressBar {
        border: 2px solid #7B59AB;
        border-radius: 5px;
        text-align: center;
        background-color: #E1E1E1;
    }
    QProgressBar::chunk {
        background-color: #00A651;
    }
    QComboBox {
        background-color: #FFFFFF;
        border: 2px solid #7B59AB;
        border-radius: 5px;
        padding: 4px;
    }
    QGroupBox {
        border: 2px solid #7B59AB;
        border-radius: 8px;
        margin-top: 10px;
        font-weight: bold;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 3px 0 3px;
    }
    TaskRowWidget {
        border-bottom: 1px solid #A1A1A1;
    }
    TaskRowWidget[completed="true"] {
        background-color: rgba(0, 166, 81, 0.1);
    }
"""

def apply_theme(theme_name=None):
    """
    Apply the specified theme to the global application instance.
    theme_name: "Light", "Dark", "System", or "SNES".
    If None, reads from QSettings.
    """
    app = QApplication.instance()
    if not app:
        return

    settings = QSettings("Hectronic", "Secretario")
    
    if not theme_name:
        theme_name = settings.value("app_theme", "System")
        
    if theme_name == "SNES":
        app.setStyleSheet(SNES_STYLESHEET)
        return

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
