"""Small localized label set for the Welcome Pomodoro action."""

from PyQt6.QtCore import QLocale


def pomodoro_labels(locale_name=None):
    language = (locale_name or QLocale.system().name()).split("_", 1)[0].lower()
    if language == "es":
        return {
            "start": "Iniciar Pomodoro",
            "open": "Abrir Pomodoro activo",
            "quick_focus": "Enfoque rápido",
            "running": "En curso",
            "paused": "En pausa",
        }
    if language == "ast":
        return {
            "start": "Entamar Pomodoro",
            "open": "Abrir Pomodoro activu",
            "quick_focus": "Enfoque rápidu",
            "running": "En cursu",
            "paused": "En pausa",
        }
    return {
        "start": "Start Pomodoro",
        "open": "Open active Pomodoro",
        "quick_focus": "Quick focus",
        "running": "Running",
        "paused": "Paused",
    }
