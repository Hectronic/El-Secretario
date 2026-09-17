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

"""Tests for the Custom Title Bar and Menus."""

import pytest
from unittest.mock import MagicMock
from PyQt6.QtCore import Qt, QPoint, QPointF
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QMainWindow, QApplication

from src.ui.main_window.title_bar import TitleBarWidget, AboutDialog


@pytest.fixture
def mock_main_window(qtbot):
    """Provides a mocked main window to host the title bar."""
    window = QMainWindow()
    window.show()
    qtbot.addWidget(window)
    return window


@pytest.fixture
def title_bar(qtbot, mock_main_window):
    """Provides a TitleBarWidget instance."""
    bar = TitleBarWidget(mock_main_window)
    qtbot.addWidget(bar)
    return bar


def test_title_bar_initialization(title_bar):
    """Test that all basic components are created successfully."""
    assert title_bar.btn_minimize is not None
    assert title_bar.btn_maximize is not None
    assert title_bar.btn_close is not None
    assert title_bar.btn_tray is not None
    assert title_bar.menu_bar is not None
    assert title_bar.icon_label is not None
    assert title_bar.setFixedHeight == 35 or title_bar.height() == 35


def test_minimize_action(title_bar, mock_main_window):
    """Test standard minimize button action."""
    title_bar._minimize_window()
    assert mock_main_window.isMinimized()


def test_toggle_maximize_action(title_bar, mock_main_window):
    """Test toggle maximize button action."""
    assert not title_bar._is_maximized
    
    title_bar._toggle_maximize()
    assert mock_main_window.isMaximized()
    assert title_bar._is_maximized
    assert title_bar.btn_maximize.text() == "🗗"

    title_bar._toggle_maximize()
    assert not mock_main_window.isMaximized()
    assert not title_bar._is_maximized
    assert title_bar.btn_maximize.text() == "🗖"


def test_minimize_to_tray_action(title_bar, mock_main_window):
    """Test minimize to tray button hides the window and alerts tray manager."""
    mock_manager = MagicMock()
    mock_main_window.system_tray_manager = mock_manager
    
    title_bar._minimize_to_tray()
    
    assert mock_main_window.isHidden()
    mock_manager.show_message.assert_called_once_with(
        "El Secretario", "Minimized to system tray. Active and ready!"
    )


def test_close_window_action(title_bar, mock_main_window):
    """Test close button action."""
    # Patch close to prevent actual app teardown
    mock_main_window.close = MagicMock()
    title_bar._close_window()
    mock_main_window.close.assert_called_once()


def test_mouse_drag_arithmetic(title_bar, mock_main_window):
    """Test dragging the title bar moves the window correctly."""
    # Initial state setup
    title_bar._is_maximized = False
    mock_main_window.move(100, 100)
    
    # Simulate mouse press at point (10, 10) relative to the widget
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(10.0, 10.0),
        QPointF(110.0, 110.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    title_bar.mousePressEvent(press_event)
    assert title_bar._drag_position is not None

    # Simulate mouse move to (150, 150) globally
    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(50.0, 50.0),
        QPointF(150.0, 150.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    title_bar.mouseMoveEvent(move_event)
    
    # Calculate expected final position of top-left corner
    # Drag pos was (110,110) - (100,100) = (10,10)
    # New top left = (150,150) - (10,10) = (140,140)
    assert mock_main_window.pos() == QPoint(140, 140)

    # Simulate mouse release
    release_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(50.0, 50.0),
        QPointF(150.0, 150.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )
    title_bar.mouseReleaseEvent(release_event)
    assert title_bar._drag_position is None


def test_mouse_double_click_maximizes(title_bar, mock_main_window):
    """Test double-clicking the title bar toggles maximize."""
    double_click = QMouseEvent(
        QMouseEvent.Type.MouseButtonDblClick,
        QPointF(20.0, 20.0),
        QPointF(120.0, 120.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    
    assert not title_bar._is_maximized
    title_bar.mouseDoubleClickEvent(double_click)
    assert title_bar._is_maximized
    assert mock_main_window.isMaximized()


def test_about_dialog_creation(qtbot):
    """Test that the About Dialog instantiates properly."""
    dlg = AboutDialog()
    qtbot.addWidget(dlg)
    assert dlg.windowTitle() == "About El Secretario"
