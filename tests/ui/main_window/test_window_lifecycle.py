from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QEvent

from src.ui.main_window.window_lifecycle import MainWindowLifecycleCoordinator


class _Tabs:
    def __init__(self, widgets):
        self.widgets = widgets

    def count(self):
        return len(self.widgets)

    def widget(self, index):
        return self.widgets[index]


class _Host:
    def __init__(self, chat_widget):
        self.chat_widget = chat_widget

    def property(self, name):
        return self.chat_widget if name == "chat_widget" else None


def test_cleanup_before_close_stops_work_and_cleans_tabs_and_floating_chats():
    tab_widget = MagicMock()
    floating_chat = MagicMock()
    host = _Host(floating_chat)
    search_thread = MagicMock()
    search_thread.isRunning.return_value = True
    recorder = MagicMock()
    recorder.is_recording = True
    window = MagicMock()
    window.central_tabs = _Tabs([tab_widget])
    window.search_thread = search_thread
    window.summary_task_queue.is_running = True
    window.recorder = recorder
    window.floating_chat_hosts = [host]

    coordinator = MainWindowLifecycleCoordinator(window)
    with patch.object(coordinator, "_release_optional_gpu_cache"):
        coordinator.cleanup_before_close()

    search_thread.requestInterruption.assert_called_once_with()
    search_thread.quit.assert_called_once_with()
    search_thread.wait.assert_called_once_with(3000)
    window.summary_task_queue.cancel_all.assert_called_once_with()
    tab_widget.cleanup.assert_called_once_with()
    floating_chat.cleanup.assert_called_once_with()
    window.chat_floating.remove_floating_host.assert_called_once_with(host)
    recorder.stop.assert_called_once_with()
    assert window.search_thread is None
    assert window.regen_worker is None
    assert window._pending_history_reload is False
    assert window._pending_tag_reload is False


def test_change_and_resize_events_delegate_to_floating_chat_coordinator():
    window = MagicMock()
    window.floating_chat_bar = object()
    coordinator = MainWindowLifecycleCoordinator(window)

    coordinator.handle_change_event(QEvent(QEvent.Type.StyleChange))
    coordinator.handle_resize()

    window.chat_floating.refresh_floating_chat_bar.assert_called_once_with()
    window.chat_floating.reposition_floating_chat_bar.assert_called_once_with()
