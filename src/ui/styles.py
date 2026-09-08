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
from src.ui.theme_styles import (
    BUTTON_DANGER_STYLE,
    BUTTON_PRIMARY_STYLE,
    DARK_STYLESHEET,
    LIGHT_STYLESHEET,
    LIST_WIDGET_STYLE,
    NEW_CHAT_BUTTON_STYLE,
    SNES_STYLESHEET,
    TEXT_EDIT_STYLE,
)

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
