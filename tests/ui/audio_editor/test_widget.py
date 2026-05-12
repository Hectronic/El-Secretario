import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import soundfile as sf
from PyQt6 import sip
from PyQt6.QtWidgets import QApplication

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from src.ui.audio_editor.widget import AudioChunk, AudioEditorWidget


class TestAudioEditorWidget(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
        cls.app.setQuitOnLastWindowClosed(False)

    @classmethod
    def tearDownClass(cls):
        if QApplication.instance():
            QApplication.instance().processEvents()
            QApplication.instance().setQuitOnLastWindowClosed(True)

    def setUp(self):
        self.db_patcher = patch("src.ui.audio_editor.widget.DBManager")
        self.mock_db = self.db_patcher.start().return_value
        self.mock_db.get_all_tags.return_value = []

        self.media_player_patcher = patch("src.ui.audio_editor.widget.QMediaPlayer")
        self.audio_output_patcher = patch("src.ui.audio_editor.widget.QAudioOutput")
        self.media_player_patcher.start()
        self.audio_output_patcher.start()

        self.recorder = MagicMock()
        self.rag = MagicMock()

    def tearDown(self):
        self.db_patcher.stop()
        self.media_player_patcher.stop()
        self.audio_output_patcher.stop()
        if QApplication.instance():
            QApplication.instance().processEvents()

    def _create_audio_file(self, tempdir, stereo=False):
        recordings_dir = os.path.join(tempdir, "recordings")
        os.makedirs(recordings_dir, exist_ok=True)
        path = os.path.join(recordings_dir, "sample.wav")
        sr = 4
        if stereo:
            left = np.array([0.1] * 4 + [0.2] * 4 + [0.3] * 4 + [0.4] * 4, dtype=np.float32)
            right = np.array([0.9] * 4 + [0.8] * 4 + [0.7] * 4 + [0.6] * 4, dtype=np.float32)
            audio = np.stack([left, right], axis=1)
        else:
            audio = np.array([0.1] * 4 + [0.2] * 4 + [0.3] * 4 + [0.4] * 4, dtype=np.float32)
        sf.write(path, audio, sr)
        return path

    def _make_widget(self, tempdir, record_id=42, stereo=False):
        audio_path = self._create_audio_file(tempdir, stereo=stereo)
        self.mock_db.fetch_record.return_value = {
            "id": record_id,
            "filename": os.path.basename(audio_path),
            "title": "Sample",
            "duration": 4.0,
        }
        widget = AudioEditorWidget(self.rag, recorder=self.recorder, record_id=record_id)
        return widget, audio_path

    def test_loads_stereo_waveform_and_chunks(self):
        tempdir = tempfile.mkdtemp(prefix="secretario_audio_editor_")
        widget, audio_path = self._make_widget(tempdir, stereo=True)
        try:
            with patch("src.ui.audio_editor.widget.os.getcwd", return_value=tempdir):
                widget.load_record(42)

            self.assertEqual(widget.current_audio.shape[1], 2)
            self.assertEqual(widget.chunk_list.count(), 1)
            self.assertEqual(widget.waveform._audio.shape[1], 2)
            self.assertAlmostEqual(widget.preview_ranges[0]["output_end"], 4.0, places=2)
        finally:
            widget.close()
            sip.delete(widget)
            self._cleanup_tempdir(tempdir)

    def test_split_cut_reorder_and_apply_edits(self):
        tempdir = tempfile.mkdtemp(prefix="secretario_audio_editor_")
        widget, audio_path = self._make_widget(tempdir, stereo=False)
        try:
            with patch("src.ui.audio_editor.widget.os.getcwd", return_value=tempdir), \
                 patch.object(widget, "_retranscribe_current_audio") as mock_retranscribe, \
                 patch("src.ui.audio_editor.widget.QMessageBox.warning") as warning_mock, \
                 patch("src.ui.audio_editor.widget.QMessageBox.critical") as critical_mock:
                widget.load_record(42)

                widget.selection_start_spin.setValue(1.0)
                widget.selection_end_spin.setValue(3.0)
                widget.split_selection()
                self.assertEqual(widget.chunk_list.count(), 3)

                widget.cut_selection()
                self.assertEqual(widget.chunk_list.count(), 2)

                widget.chunk_list.setCurrentRow(1)
                widget.move_chunk(-1)
                self.assertEqual(widget.chunk_list.count(), 2)
                self.assertAlmostEqual(widget.preview_ranges[0]["source_start"], 3.0, places=2)
                self.assertAlmostEqual(widget.preview_ranges[1]["source_start"], 0.0, places=2)

                result = widget.apply_edits()
                self.assertTrue(result)

            edited = sf.read(audio_path, always_2d=False)[0]
            self.assertAlmostEqual(float(edited[0]), 0.4, places=2)
            self.assertAlmostEqual(float(edited[4]), 0.1, places=2)
            mock_retranscribe.assert_called_once()
            warning_mock.assert_not_called()
            critical_mock.assert_not_called()
        finally:
            widget.close()
            sip.delete(widget)
            self._cleanup_tempdir(tempdir)

    def test_manual_chunk_reorder_changes_preview_order(self):
        tempdir = tempfile.mkdtemp(prefix="secretario_audio_editor_")
        widget, audio_path = self._make_widget(tempdir, stereo=False)
        try:
            with patch("src.ui.audio_editor.widget.os.getcwd", return_value=tempdir):
                widget.load_record(42)
                widget.chunks = [
                    AudioChunk(0.0, 1.0),
                    AudioChunk(1.0, 2.0),
                    AudioChunk(2.0, 3.0),
                    AudioChunk(3.0, 4.0),
                ]
                widget.active_chunk_index = 2
                widget._rebuild_preview()
                widget.move_chunk(-1)

            self.assertAlmostEqual(widget.preview_ranges[0]["source_start"], 0.0, places=2)
            self.assertAlmostEqual(widget.preview_ranges[1]["source_start"], 2.0, places=2)
            self.assertAlmostEqual(widget.preview_ranges[2]["source_start"], 1.0, places=2)
            self.assertAlmostEqual(widget.preview_ranges[3]["source_start"], 3.0, places=2)
        finally:
            widget.close()
            sip.delete(widget)
            self._cleanup_tempdir(tempdir)

    def test_adjust_active_chunk_boundary_updates_neighbor_segments(self):
        tempdir = tempfile.mkdtemp(prefix="secretario_audio_editor_")
        widget, audio_path = self._make_widget(tempdir, stereo=False)
        try:
            with patch("src.ui.audio_editor.widget.os.getcwd", return_value=tempdir):
                widget.load_record(42)
                widget.chunks = [
                    AudioChunk(0.0, 2.0),
                    AudioChunk(2.0, 4.0),
                ]
                widget.active_chunk_index = 0
                widget._rebuild_preview()

                changed = widget.adjust_active_chunk_boundary("right", 1.5)

            self.assertTrue(changed)
            self.assertAlmostEqual(widget.chunks[0].source_end, 1.5, places=2)
            self.assertAlmostEqual(widget.chunks[1].source_start, 1.5, places=2)
            self.assertAlmostEqual(widget.preview_ranges[0]["output_end"], 1.5, places=2)
            self.assertAlmostEqual(widget.preview_ranges[1]["output_start"], 1.5, places=2)
        finally:
            widget.close()
            sip.delete(widget)
            self._cleanup_tempdir(tempdir)

    def test_waveform_chunk_click_selects_chunk_in_editor(self):
        tempdir = tempfile.mkdtemp(prefix="secretario_audio_editor_")
        widget, _audio_path = self._make_widget(tempdir, stereo=False)
        try:
            with patch("src.ui.audio_editor.widget.os.getcwd", return_value=tempdir):
                widget.load_record(42)
                widget.chunks = [
                    AudioChunk(0.0, 2.0),
                    AudioChunk(2.0, 4.0),
                ]
                widget.active_chunk_index = 0
                widget._rebuild_preview()

                widget.waveform.chunk_clicked.emit(1)

            self.assertEqual(widget.active_chunk_index, 1)
            self.assertEqual(widget.chunk_list.currentRow(), 1)
            self.assertAlmostEqual(widget.selection_start_spin.value(), 2.0, places=2)
            self.assertAlmostEqual(widget.selection_end_spin.value(), 4.0, places=2)
        finally:
            widget.close()
            sip.delete(widget)
            self._cleanup_tempdir(tempdir)

    def test_undo_redo_restores_and_reapplies_split(self):
        tempdir = tempfile.mkdtemp(prefix="secretario_audio_editor_")
        widget, _audio_path = self._make_widget(tempdir, stereo=False)
        try:
            with patch("src.ui.audio_editor.widget.os.getcwd", return_value=tempdir):
                widget.load_record(42)
                widget.selection_start_spin.setValue(1.0)
                widget.selection_end_spin.setValue(3.0)
                widget.split_selection()
                self.assertEqual(widget.chunk_list.count(), 3)

                undo_ok = widget.undo()
                self.assertTrue(undo_ok)
                self.assertEqual(widget.chunk_list.count(), 1)

                redo_ok = widget.redo()
                self.assertTrue(redo_ok)
                self.assertEqual(widget.chunk_list.count(), 3)
        finally:
            widget.close()
            sip.delete(widget)
            self._cleanup_tempdir(tempdir)

    def test_keyboard_shortcuts_trigger_undo_redo(self):
        tempdir = tempfile.mkdtemp(prefix="secretario_audio_editor_")
        widget, _audio_path = self._make_widget(tempdir, stereo=False)
        try:
            with patch("src.ui.audio_editor.widget.os.getcwd", return_value=tempdir):
                widget.load_record(42)
                widget.selection_start_spin.setValue(1.0)
                widget.selection_end_spin.setValue(3.0)
                widget.split_selection()
                self.assertEqual(widget.chunk_list.count(), 3)

                widget.undo_shortcut.activated.emit()
                self.assertEqual(widget.chunk_list.count(), 1)

                widget.redo_shortcut.activated.emit()
                self.assertEqual(widget.chunk_list.count(), 3)
        finally:
            widget.close()
            sip.delete(widget)
            self._cleanup_tempdir(tempdir)

    def _cleanup_tempdir(self, tempdir):
        if not os.path.isdir(tempdir):
            return
        for root, _dirs, files in os.walk(tempdir, topdown=False):
            for name in files:
                try:
                    os.remove(os.path.join(root, name))
                except OSError:
                    pass
            try:
                os.rmdir(root)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
