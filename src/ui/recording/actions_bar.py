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

from PyQt6.QtWidgets import QHBoxLayout

from src.ui.recording.controls import create_danger_action, create_primary_action, create_secondary_action


@dataclass
class ActionsBar:
    layout: QHBoxLayout
    summarize_btn: object
    extract_tasks_btn: object
    save_all_btn: object
    ask_meeting_btn: object
    delete_btn: object


def build_actions_bar(parent, *, summarize_slot, extract_tasks_slot, save_slot, ask_slot, delete_slot):
    layout = QHBoxLayout()
    layout.setSpacing(12)
    layout.setContentsMargins(0, 6, 0, 2)

    ai_layout = QHBoxLayout()
    ai_layout.setSpacing(10)
    summarize_btn = create_secondary_action(
        "Summarize (AI)",
        summarize_slot,
        min_height=36,
        enabled=False,
        parent=parent,
    )
    ai_layout.addWidget(summarize_btn)

    extract_tasks_btn = create_secondary_action(
        "Extract Tasks (AI)",
        extract_tasks_slot,
        min_height=36,
        enabled=False,
        parent=parent,
    )
    ai_layout.addWidget(extract_tasks_btn)

    layout.addLayout(ai_layout)

    save_all_btn = create_primary_action(
        "Save All Changes",
        save_slot,
        min_height=36,
        enabled=False,
        parent=parent,
    )
    layout.addWidget(save_all_btn)
    layout.addStretch()

    ask_meeting_btn = create_primary_action(
        "Ask About This Meeting",
        ask_slot,
        min_height=38,
        enabled=False,
        parent=parent,
    )
    layout.addWidget(ask_meeting_btn)
    layout.addSpacing(18)

    delete_btn = create_danger_action(
        "Delete",
        delete_slot,
        min_height=38,
        min_width=110,
        enabled=False,
        parent=parent,
    )
    layout.addWidget(delete_btn)
    layout.addSpacing(8)

    return ActionsBar(
        layout=layout,
        summarize_btn=summarize_btn,
        extract_tasks_btn=extract_tasks_btn,
        save_all_btn=save_all_btn,
        ask_meeting_btn=ask_meeting_btn,
        delete_btn=delete_btn,
    )
