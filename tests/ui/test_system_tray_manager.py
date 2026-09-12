import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from unittest.mock import MagicMock
from src.ui.system_tray_manager import SystemTrayManager

@pytest.fixture
def main_window_mock(qapp, monkeypatch):
    from PyQt6.QtWidgets import QSystemTrayIcon
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", lambda: True)
    
    window = MagicMock()
    window.windowIcon.return_value = QIcon()
    window.isVisible.return_value = True
    return window

def test_system_tray_manager_initializes(main_window_mock, qapp):
    manager = SystemTrayManager(main_window_mock)
    assert manager._tray_icon is not None
    assert manager.toggle_window_action.text() == "Show El Secretario"
    assert manager._menu is not None

def test_set_recording_state_updates_icon(main_window_mock, qapp):
    manager = SystemTrayManager(main_window_mock)
    manager.set_recording_state(True)
    assert manager._is_recording is True
    # Verify tooltip updated
    assert manager._tray_icon.toolTip() == "El Secretario - Recording in Progress"

    manager.set_recording_state(False)
    assert manager._is_recording is False
    assert manager._tray_icon.toolTip() == "El Secretario"

def test_bind_recording_actions(main_window_mock, qapp):
    manager = SystemTrayManager(main_window_mock)
    stop_cb = MagicMock()
    pause_cb = MagicMock()
    cancel_cb = MagicMock()

    manager.bind_recording_actions(stop_cb, pause_cb, cancel_cb)
    assert manager.pause_recording_action.isVisible() is True
    assert manager.stop_recording_action.isVisible() is True
    assert manager.cancel_recording_action.isVisible() is True

    manager.unbind_recording_actions()
    assert manager.pause_recording_action.isVisible() is False

def test_toggle_main_window(main_window_mock, qapp):
    manager = SystemTrayManager(main_window_mock)
    
    # Simulate window is visible
    main_window_mock.isVisible.return_value = True
    manager._toggle_main_window()
    main_window_mock.hide.assert_called_once()
    assert manager.toggle_window_action.text() == "Show El Secretario"

    # Simulate window is hidden
    main_window_mock.isVisible.return_value = False
    manager._toggle_main_window()
    main_window_mock.showNormal.assert_called_once()
    main_window_mock.activateWindow.assert_called_once()
    main_window_mock.raise_.assert_called_once()
    assert manager.toggle_window_action.text() == "Hide El Secretario"

def test_on_quit_triggered(main_window_mock, qapp):
    manager = SystemTrayManager(main_window_mock)
    quit_signal_called = False
    
    def on_quit():
        nonlocal quit_signal_called
        quit_signal_called = True
        
    manager.quit_requested.connect(on_quit)
    manager._on_quit_triggered()
    
    assert quit_signal_called is True
    assert manager._tray_icon is None
