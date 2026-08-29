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

from dataclasses import dataclass

from PyQt6.QtWidgets import QHBoxLayout, QTabWidget, QTextEdit, QVBoxLayout, QWidget

from src.ui.recording.controls import create_action_button, create_secondary_action
from src.ui.tasks_list_widget import TasksListWidget


@dataclass
class ContentTabs:
    tabs: QTabWidget
    text_display: QTextEdit
    notes_display: QTextEdit
    summary_display: QTextEdit
    tasks_widget: TasksListWidget
    rename_speakers_btn: object
    copy_transcription_btn: object


def build_content_tabs(
    parent,
    db,
    record_id,
    *,
    open_speaker_manager,
    copy_transcription,
    on_transcription_text_changed,
):
    tabs = QTabWidget()
    original_widget = QWidget()
    original_layout = QVBoxLayout(original_widget)
    toolbar = QHBoxLayout()

    rename_speakers_btn = create_action_button(
        "Rename Speakers",
        open_speaker_manager,
        enabled=False,
        parent=parent,
    )
    toolbar.addWidget(rename_speakers_btn)

    copy_transcription_btn = create_secondary_action(
        "Copy Transcription",
        copy_transcription,
        tooltip="Copy the full transcription to the clipboard",
        enabled=False,
        parent=parent,
    )
    toolbar.addWidget(copy_transcription_btn)
    toolbar.addStretch()
    original_layout.addLayout(toolbar)

    text_display = QTextEdit()
    text_display.setPlaceholderText("Transcription will appear here...")
    text_display.textChanged.connect(on_transcription_text_changed)
    original_layout.addWidget(text_display)
    tabs.addTab(original_widget, "Original")

    notes_display = QTextEdit()
    notes_display.setPlaceholderText("Add notes for this recording...")
    tabs.addTab(notes_display, "Notes")

    summary_display = QTextEdit()
    summary_display.setReadOnly(True)
    summary_display.setPlaceholderText("Summary will appear here...")
    tabs.addTab(summary_display, "Summary")

    tasks_widget = TasksListWidget(db, record_id=record_id, parent=parent)
    tabs.addTab(tasks_widget, "Tasks")

    return ContentTabs(
        tabs=tabs,
        text_display=text_display,
        notes_display=notes_display,
        summary_display=summary_display,
        tasks_widget=tasks_widget,
        rename_speakers_btn=rename_speakers_btn,
        copy_transcription_btn=copy_transcription_btn,
    )
