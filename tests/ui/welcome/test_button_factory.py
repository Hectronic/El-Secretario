# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
from PyQt6.QtWidgets import QApplication

from src.ui.welcome.button_factory import (
    create_big_button,
    create_round_button,
    create_squircle_button,
)


_APP = None


def _ensure_app():
    global _APP
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    _APP = app
    return app


def test_create_big_button_sets_callback_size_and_classless_style():
    _ensure_app()
    calls = []
    button = create_big_button("Buscar", "#1565C0", lambda: calls.append(True), width=150, height=44)

    button.click()

    assert button.text() == "Buscar"
    assert button.width() == 150
    assert button.height() == 44
    assert "background-color: #1565C0;" in button.styleSheet()
    assert calls == [True]


def test_create_round_button_uses_class_property_when_requested():
    _ensure_app()
    button = create_round_button("REC", "#f44336", lambda: None, size=85, class_name="rec-btn")

    assert button.property("class") == "rec-btn"
    assert button.width() == 85
    assert button.height() == 85
    assert button.styleSheet() == ""


def test_create_squircle_button_uses_qcolor_shading_for_default_style():
    _ensure_app()
    button = create_squircle_button("NOTE", "#2196F3", lambda: None, width=110, height=160)

    assert button.width() == 110
    assert button.height() == 160
    assert "border-top-right-radius: 40px;" in button.styleSheet()
    assert "background-color: #2196F3;" in button.styleSheet()
