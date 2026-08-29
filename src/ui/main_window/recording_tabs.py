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

from src.ui.audio_editor.widget import AudioEditorWidget
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

    def _wire_recording_widget(self, rec_widget):
        rec_widget.recording_saved.connect(lambda w=rec_widget: self.window._handle_recording_widget_saved(w))
        rec_widget.recording_deleted.connect(self.window._handle_recording_widget_deleted)
        rec_widget.status_changed.connect(self.window.handle_status_message)
        rec_widget.progress_changed.connect(self.window.handle_progress)
        if hasattr(rec_widget, "start_chat_requested"):
            rec_widget.start_chat_requested.connect(lambda contexts: self.window.open_chat_tab(initial_contexts=contexts))
        if hasattr(rec_widget, "open_audio_editor_requested"):
            rec_widget.open_audio_editor_requested.connect(self.window.open_recording_editor_tab)
        rec_widget.close_requested.connect(lambda: self.window.close_tab(self.window.central_tabs.indexOf(rec_widget)))
