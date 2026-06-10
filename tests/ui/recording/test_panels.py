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
# along with this program.  See <https://www.gnu.org/licenses/>.

from unittest.mock import MagicMock

from PyQt6.QtWidgets import QApplication, QWidget

from src.ui.recording.actions_bar import build_actions_bar
from src.ui.recording.content_tabs import build_content_tabs
from src.ui.recording.metadata_panel import build_metadata_panel
from src.ui.recording.transcription_panel import build_transcription_panel


APP = QApplication.instance() or QApplication([])


class FakeTasksDb:
    def get_all_tags(self):
        return []

    def get_tasks_by_record(self, record_id):
        return []


def test_build_transcription_panel_exposes_expected_controls():
    parent = QWidget()
    try:
        panel = build_transcription_panel(parent, lambda: None)

        assert panel.model_combo.currentText()
        assert panel.lang_combo.currentText() == "Auto"
        assert panel.diarization_check.text() == "Diarization"
        assert panel.retranscribe_btn.text() == "Retranscribe"
        assert panel.retranscribe_btn.property("class") == "calendar-primary-btn"
        assert not panel.retranscribe_btn.isEnabled()
    finally:
        parent.close()


def test_build_metadata_panel_uses_disabled_empty_record_defaults():
    panel = build_metadata_panel(["ops", "sales"])

    assert panel.group.title() == "Recording Details"
    assert panel.title_input.placeholderText() == "Enter title..."
    assert not panel.title_input.isEnabled()
    assert panel.date_label.text() == "-"
    assert panel.duration_label.text() == "-"
    assert not panel.tags_input.isEnabled()
    assert not panel.is_diarized_check.isEnabled()


def test_build_content_tabs_preserves_tab_contract_and_toolbar_actions():
    parent = QWidget()
    changed = []
    try:
        panel = build_content_tabs(
            parent,
            FakeTasksDb(),
            3,
            open_speaker_manager=lambda: None,
            copy_transcription=lambda: None,
            on_transcription_text_changed=lambda: changed.append(True),
        )

        assert panel.tabs.count() == 4
        assert [panel.tabs.tabText(i) for i in range(panel.tabs.count())] == [
            "Original",
            "Notes",
            "Summary",
            "Tasks",
        ]
        assert panel.rename_speakers_btn.text() == "Rename Speakers"
        assert panel.copy_transcription_btn.text() == "Copy Transcription"
        assert panel.copy_transcription_btn.property("class") == "calendar-nav-btn"
        panel.text_display.setPlainText("Transcript")
        assert changed
    finally:
        parent.close()


def test_build_actions_bar_preserves_action_text_styles_and_disabled_defaults():
    parent = QWidget()
    slots = {name: MagicMock() for name in ("summary", "tasks", "save", "ask", "delete")}
    try:
        actions = build_actions_bar(
            parent,
            summarize_slot=slots["summary"],
            extract_tasks_slot=slots["tasks"],
            save_slot=slots["save"],
            ask_slot=slots["ask"],
            delete_slot=slots["delete"],
        )

        assert actions.summarize_btn.property("class") == "calendar-nav-btn"
        assert actions.extract_tasks_btn.property("class") == "calendar-nav-btn"
        assert actions.save_all_btn.property("class") == "calendar-primary-btn"
        assert actions.ask_meeting_btn.property("class") == "calendar-primary-btn"
        assert actions.delete_btn.property("class") == "record-del-btn"
        assert not actions.save_all_btn.isEnabled()
        assert not actions.ask_meeting_btn.isEnabled()
        assert not actions.delete_btn.isEnabled()
    finally:
        parent.close()
