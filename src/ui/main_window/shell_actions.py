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

"""Main-window shell actions that coordinate the outer UI chrome."""

from src.ui.welcome_widget import WelcomeWidget


class MainWindowShellCoordinator:
    """Own welcome-tab wiring, accordion state, and central-tab synchronization."""

    def __init__(self, window):
        self.window = window

    def on_right_section_header_clicked(self, section_key):
        if self.window._active_right_section == section_key:
            self.set_active_right_section(None)
        else:
            self.set_active_right_section(section_key)

    def set_active_right_section(self, section_key):
        window = self.window
        if section_key is not None and section_key not in window._right_sidebar_sections:
            return

        window._active_right_section = section_key
        if section_key not in (None, "chat_context"):
            window._right_sidebar_last_non_chat_section = section_key
        for key, section in window._right_sidebar_sections.items():
            is_active = section_key is not None and key == section_key
            section["header"].blockSignals(True)
            section["header"].setChecked(is_active)
            prefix = "▾ " if is_active else "▸ "
            section["header"].setText(f"{prefix}{section['title']}")
            section["header"].blockSignals(False)
            header_shell = section.get("header_shell")
            if header_shell is not None:
                header_shell.setProperty("active", "true" if is_active else "false")
                header_shell.style().unpolish(header_shell)
                header_shell.style().polish(header_shell)
            section["content"].setVisible(is_active)
            index = section.get("index")
            if window._right_sidebar_layout is not None and index is not None:
                window._right_sidebar_layout.setStretch(
                    index, 1 if section_key is not None and is_active else 0
                )
        if window._right_sidebar_layout is not None and window._right_sidebar_bottom_spacer_index is not None:
            window._right_sidebar_layout.setStretch(
                window._right_sidebar_bottom_spacer_index,
                0 if section_key is not None else 1,
            )

    def on_central_tab_changed(self, _index):
        self.window.refresh_tasks_sidebar()
        self.window._sync_chat_context_section()

    def show_welcome_screen(self):
        window = self.window
        window.welcome_widget = WelcomeWidget(window.db)
        welcome = window.welcome_widget
        welcome.new_recording_requested.connect(window.start_new_recording)
        welcome.new_note_requested.connect(lambda: window.open_note_tab(None))
        welcome.search_triggered.connect(window.perform_welcome_search)
        welcome.result_clicked.connect(window.open_item_tab)
        welcome.new_chat_requested.connect(lambda: window.open_chat_tab(None))
        welcome.ask_chat_with_context_requested.connect(window.open_chat_tab_from_current_context)
        welcome.import_audio_requested.connect(window.import_audio_file)
        welcome.notebooks_requested.connect(window.open_notebooks_list)
        welcome.tools_requested.connect(lambda: window.open_tools_tab())
        welcome.settings_requested.connect(window.open_settings_tab)
        welcome.generate_daily_summary_requested.connect(window.generate_today_daily_summary)
        welcome.status_message_requested.connect(window.handle_status_message)
        window.central_tabs.addTab(welcome, "Welcome")
        window._set_tab_action_buttons(welcome)
