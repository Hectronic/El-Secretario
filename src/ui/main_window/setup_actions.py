# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import logging
import os
import shutil

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from src.ui.settings.widget import SettingsWidget


class SetupActionsCoordinator:
    """Coordinate setup-related actions owned by MainWindow."""

    def __init__(self, window):
        self.window = window

    def open_settings_tab(self):
        """Open the settings widget in the central tab bar, reusing it if present."""
        for i in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(i)
            if isinstance(widget, SettingsWidget):
                self.window.central_tabs.setCurrentIndex(i)
                return

        settings_widget = SettingsWidget()
        settings_widget.rag_initialize_requested.connect(
            lambda cfg: self.window._build_rag_engine(cfg, reason="initialize")
        )
        settings_widget.rag_reload_requested.connect(
            lambda cfg: self.window._build_rag_engine(cfg, reason="reload")
        )
        settings_widget.rag_reindex_requested.connect(
            lambda: self.window.summary_task_queue.enqueue_rag_reindex(source="settings")
        )
        index = self.window.central_tabs.addTab(settings_widget, "Settings")
        self.window.central_tabs.setCurrentIndex(index)

    def import_audio_file(self, config):
        """Import an audio file and start transcription with the provided config."""
        file_path, _ = QFileDialog.getOpenFileName(
            self.window,
            "Import Audio",
            "",
            "Audio Files (*.wav *.mp3 *.m4a *.ogg *.flac);;All Files (*)",
        )
        if not file_path:
            return

        try:
            recordings_dir = os.path.join(os.getcwd(), "recordings")
            os.makedirs(recordings_dir, exist_ok=True)

            filename = os.path.basename(file_path)
            dest_path = os.path.join(recordings_dir, filename)

            # Keep imported filenames unique to avoid overwriting existing recordings.
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(filename)
                i = 1
                while os.path.exists(dest_path):
                    new_filename = f"{base}_{i}{ext}"
                    dest_path = os.path.join(recordings_dir, new_filename)
                    i += 1
                filename = os.path.basename(dest_path)

            shutil.copy2(file_path, dest_path)
            record_id = self.window.db.save(filename, "", 0.0, title=filename)
            rec_widget = self.window.open_recording_tab(record_id, config)

            if rec_widget is not None and hasattr(rec_widget, "start_transcription_with_config"):
                rec_widget.start_transcription_with_config(dest_path, config)
        except Exception as exc:
            logging.exception("Failed to import audio file.")
            QMessageBox.critical(self.window, "Import Error", f"Failed to import audio: {exc}")
