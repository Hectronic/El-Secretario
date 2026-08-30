# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import logging
import os

from PyQt6.QtWidgets import QMessageBox

from src.ui.audio_editor.widget import AudioEditorWidget
from src.ui.recording_in_progress_widget import RecordingInProgressWidget
from src.ui.recording_widget import RecordingWidget


class RecordingTabCoordinator:
    """Own the tab lifecycle for recording and audio editing views."""

    def __init__(self, window):
        self.window = window

    def recording_tab_title(self, record):
        if not record:
            return "New Recording"
        title = record.get("title") or ""
        if title:
            return title
        filename = record.get("filename") or ""
        if filename:
            return filename
        record_id = record.get("id")
        return f"Recording {record_id}" if record_id is not None else "New Recording"

    def find_recording_tabs(self, record_id):
        tabs = []
        for i in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(i)
            if isinstance(widget, RecordingWidget) and widget.current_record_id == record_id:
                tabs.append(widget)
        return tabs

    def sync_recording_tab_titles(self, record_id):
        record = self.window.db.fetch_record(record_id)
        title = self.recording_tab_title(record) if record else f"Recording {record_id}"
        for i in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(i)
            if isinstance(widget, RecordingWidget) and widget.current_record_id == record_id:
                self.window.central_tabs.setTabText(i, title)

    def close_recording_tabs(self, record_id):
        removed = False
        for i in range(self.window.central_tabs.count() - 1, -1, -1):
            widget = self.window.central_tabs.widget(i)
            if isinstance(widget, RecordingWidget) and widget.current_record_id == record_id:
                if hasattr(widget, "cleanup"):
                    try:
                        widget.cleanup()
                    except Exception:
                        pass
                self.window.central_tabs.removeTab(i)
                widget.deleteLater()
                removed = True
        if removed and self.window.central_tabs.count() == 0:
            self.window.show_welcome_screen()
        if removed:
            self.window._sync_chat_context_section()

    def open_recording_tab(self, record_id, config=None, force_new=False):
        if record_id is not None and not force_new:
            for i in range(self.window.central_tabs.count()):
                widget = self.window.central_tabs.widget(i)
                if isinstance(widget, RecordingWidget) and widget.current_record_id == record_id:
                    self.window.central_tabs.setCurrentIndex(i)
                    return widget

        rec_widget = RecordingWidget(
            self.window.rag,
            recorder=self.window.recorder,
            record_id=record_id,
            task_queue=self.window.summary_task_queue,
        )
        self._wire_recording_widget(rec_widget)

        if config:
            rec_widget.set_transcription_config(config)

        title = "New Recording"
        if record_id:
            record = self.window.db.fetch_record(record_id)
            if not isinstance(record, dict):
                records = self.window.db.fetch_all()
                record = next((r for r in records if r["id"] == record_id), None)
            if record:
                title = self.recording_tab_title(record)

        index = self.window.central_tabs.addTab(rec_widget, title)
        self.window.central_tabs.setCurrentIndex(index)
        return rec_widget

    def open_recording_editor_tab(self, record_id, config=None):
        rec_widget = AudioEditorWidget(
            self.window.rag,
            recorder=self.window.recorder,
            record_id=record_id,
            task_queue=self.window.summary_task_queue,
        )
        self._wire_recording_widget(rec_widget)

        title = "Audio Editor"
        if record_id:
            record = self.window.db.fetch_record(record_id)
            if not isinstance(record, dict):
                records = self.window.db.fetch_all()
                record = next((r for r in records if r["id"] == record_id), None)
            if record:
                title = f"{self.recording_tab_title(record)} - Editor"

        index = self.window.central_tabs.addTab(rec_widget, title)
        self.window.central_tabs.setCurrentIndex(index)
        return rec_widget

    def start_new_recording(self, config):
        """Open or focus the in-progress recording tab for ``config``."""
        window = self.window
        logging.info("Starting new recording with config: %s", config)
        window._log_user_settings_snapshot("start_new_recording")
        for index in range(window.central_tabs.count()):
            widget = window.central_tabs.widget(index)
            if isinstance(widget, RecordingInProgressWidget):
                window.central_tabs.setCurrentIndex(index)
                return

        if config.get("device_index") is not None:
            window.recorder.set_device(config["device_index"])
        window.recorder.set_capture_machine_audio(config.get("capture_system_audio", False))

        rec_widget = RecordingInProgressWidget(recorder=window.recorder, config=config)
        rec_widget.finished.connect(
            lambda path, finished_config, widget=rec_widget: self.on_recording_finished(
                path, finished_config, widget
            )
        )
        rec_widget.cancelled.connect(
            lambda widget=rec_widget: window.close_tab(window.central_tabs.indexOf(widget))
        )
        index = window.central_tabs.addTab(rec_widget, "Recording...")
        window.central_tabs.setCurrentIndex(index)

    def handle_recording_widget_saved(self, rec_widget):
        record_id = getattr(rec_widget, "current_record_id", None)
        if record_id is None:
            return
        self.window.load_history()
        self.window.request_sidebar_reload(include_tags=True, include_history=True)
        self.sync_recording_tab_titles(record_id)

    def handle_recording_widget_deleted(self, record_id):
        self.close_recording_tabs(record_id)
        self.window.load_history()
        self.window.request_sidebar_reload(include_tags=True, include_history=True)

    def on_recording_finished(self, file_path, config, widget):
        """Persist a completed capture, open it, and start its transcription."""
        window = self.window
        window._log_user_settings_snapshot("on_recording_finished")
        logging.info(
            "on_recording_finished called with file_path=%s widget=%s config_keys=%s",
            file_path,
            type(widget).__name__ if widget else None,
            sorted(list((config or {}).keys())),
        )
        index = window.central_tabs.indexOf(widget)
        if index != -1:
            window.central_tabs.removeTab(index)
            widget.deleteLater()
            logging.info("RecordingInProgress tab closed at index=%s", index)
        else:
            logging.warning("RecordingInProgress widget tab not found during finish flow.")

        try:
            filename = os.path.basename(file_path)
            title = config.get("title") or filename
            recording_notes = config.get("recording_notes", "")
            pending_tasks = config.get("pending_tasks") or []
            logging.info(
                "Persisting new recording filename=%s title=%s notes_len=%d pending_tasks=%d",
                filename,
                title,
                len(recording_notes),
                len(pending_tasks),
            )
            record_id = window.db.save(
                filename, "", 0.0, title=title, recording_notes=recording_notes
            )
            tags = config.get("tags", "")
            if tags:
                window.db.update_tags(record_id, tags)
            for task_content in pending_tasks:
                clean_task = str(task_content or "").strip()
                if not clean_task:
                    continue
                try:
                    window.db.save_task(record_id=record_id, content=clean_task, tags=tags or None)
                except Exception:
                    logging.exception("Failed saving quick task for record_id=%s", record_id)

            window.request_sidebar_reload(include_tags=True, include_history=True)
            rec_widget = self.open_recording_tab(record_id, config)
            if rec_widget and isinstance(rec_widget, RecordingWidget):
                logging.info(
                    "Starting transcription with config for record_id=%s file=%s", record_id, file_path
                )
                rec_widget.start_transcription_with_config(file_path, config)
        except Exception as error:
            logging.exception("Failed while handling recording completion flow.")
            QMessageBox.critical(window, "Error", f"Failed to save recording: {error}")

    def _wire_recording_widget(self, rec_widget):
        rec_widget.recording_saved.connect(lambda w=rec_widget: self.handle_recording_widget_saved(w))
        rec_widget.recording_deleted.connect(self.handle_recording_widget_deleted)
        rec_widget.status_changed.connect(self.window.handle_status_message)
        rec_widget.progress_changed.connect(self.window.handle_progress)
        if hasattr(rec_widget, "start_chat_requested"):
            rec_widget.start_chat_requested.connect(lambda contexts: self.window.open_chat_tab(initial_contexts=contexts))
        if hasattr(rec_widget, "open_audio_editor_requested"):
            rec_widget.open_audio_editor_requested.connect(self.window.open_recording_editor_tab)
        rec_widget.close_requested.connect(lambda: self.window.close_tab(self.window.central_tabs.indexOf(rec_widget)))
