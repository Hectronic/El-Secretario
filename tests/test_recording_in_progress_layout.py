import os
import sys
import unittest
from unittest.mock import patch

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import QApplication

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ui.recording_in_progress_widget import RecordingInProgressWidget


class _FakeRecorder(QObject):
    amplitude_changed = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.is_recording = False
        self.is_paused = False
        self.device_index = None
        self.capture_system_audio = False

    def set_device(self, device_index):
        self.device_index = device_index

    def set_capture_machine_audio(self, enabled):
        self.capture_system_audio = bool(enabled)

    def start(self):
        self.is_recording = True

    def stop(self):
        self.is_recording = False
        return "fake.wav"

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False


class TestRecordingInProgressLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    @patch("src.ui.recording_in_progress_widget.DBManager")
    def test_layout_uses_scroll_container(self, mock_db):
        mock_db.return_value.get_all_tags.return_value = []
        widget = RecordingInProgressWidget(recorder=_FakeRecorder(), config={})
        try:
            self.assertTrue(hasattr(widget, "scroll_area"))
            self.assertTrue(widget.scroll_area.widgetResizable())
            self.assertIsNotNone(widget.scroll_area.widget())
        finally:
            widget.cleanup()
            widget.deleteLater()

    @patch("src.ui.recording_in_progress_widget.DBManager")
    def test_compact_mode_reduces_heights_and_stacks_workspace(self, mock_db):
        mock_db.return_value.get_all_tags.return_value = []
        widget = RecordingInProgressWidget(recorder=_FakeRecorder(), config={})
        try:
            widget._apply_layout_density(viewport_height=700)
            self.assertTrue(widget._compact_mode_active)
            self.assertEqual(widget.vu_meter.width(), 320)
            self.assertEqual(widget.pause_btn.height(), 44)
            self.assertEqual(widget.stop_btn.height(), 44)
            self.assertEqual(widget.notes_input.minimumHeight(), 160)
            self.assertEqual(widget.workspace_split.orientation(), Qt.Orientation.Vertical)

            widget._apply_layout_density(viewport_height=1200)
            self.assertFalse(widget._compact_mode_active)
            self.assertEqual(widget.vu_meter.width(), 400)
            self.assertEqual(widget.pause_btn.height(), 50)
            self.assertEqual(widget.stop_btn.height(), 50)
            self.assertEqual(widget.notes_input.minimumHeight(), 220)
            self.assertEqual(widget.workspace_split.orientation(), Qt.Orientation.Horizontal)
        finally:
            widget.cleanup()
            widget.deleteLater()
