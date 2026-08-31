from unittest.mock import patch

from src.ui.main_window import MainWindow


def test_main_window_init_ui_delegates_to_layout_builder():
    window = object()

    with patch("src.ui.main_window.build_main_window_layout") as build_layout:
        MainWindow.init_ui(window)

    build_layout.assert_called_once_with(window)
