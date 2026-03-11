import unittest
from unittest.mock import MagicMock

from src.ui.main_window import MainWindow


class TestMainWindowStatusMessage(unittest.TestCase):
    def test_handle_status_message_before_task_label_exists(self):
        window = MainWindow.__new__(MainWindow)
        window.summary_task_queue = MagicMock()
        window.summary_task_queue.is_running = False
        status_bar = MagicMock()
        window.statusBar = MagicMock(return_value=status_bar)

        # Should not raise even if task_status_label is not initialized yet.
        window.handle_status_message("Booting")
        status_bar.showMessage.assert_called_once()

