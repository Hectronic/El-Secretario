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

from PyQt6.QtCore import QDate

from src.ui.chat.session_state import (
    build_chat_session_payload,
    build_new_chat_session_name,
    persist_chat_session,
    resolve_chat_display_title,
)


class _Panel:
    def __init__(self):
        self.current_week_monday = None
        self.current_date_filter = None
        self._tags = []
        self._notebooks = []

    def get_active_tags(self):
        return list(self._tags)

    def get_active_notebooks(self):
        return list(self._notebooks)


def test_build_new_chat_session_name_uses_first_message():
    assert build_new_chat_session_name([{"content": "Hello world"}]) == "Hello world"


def test_resolve_chat_display_title_prefers_session_name():
    assert resolve_chat_display_title("Session A", [], [], [], None) == "Session A"


def test_resolve_chat_display_title_falls_back_to_labels():
    title = resolve_chat_display_title(None, [], ["Pinned"], ["ops"], "2026-03-10")
    assert title == "Pinned, ops..."


def test_build_chat_session_payload_serializes_context_and_messages():
    panel = _Panel()
    panel.current_week_monday = QDate(2026, 3, 9)
    panel.current_date_filter = "2026-03-15"
    panel._tags = ["ops"]
    panel._notebooks = [2]

    payload = build_chat_session_payload([{"role": "user", "content": "Hi"}], panel, {7})

    assert payload["name"] == "Hi"
    assert '"role": "user"' in payload["messages_json"]
    assert '"type": "recording"' in payload["context_json"]
    assert '"type": "notebook"' in payload["context_json"]


def test_persist_chat_session_creates_when_missing():
    db = type("DB", (), {})()
    calls = {}

    def save_chat_session(name, collection, messages_json, context_data=None):
        calls["save"] = (name, collection, messages_json, context_data)
        return 42

    db.save_chat_session = save_chat_session
    db.update_chat_session = lambda *args, **kwargs: None

    panel = _Panel()
    panel._tags = ["ops"]

    session_id = persist_chat_session(db, None, [{"role": "user", "content": "Hi"}], panel, {7})

    assert session_id == 42
    assert calls["save"][0] == "Hi"
    assert calls["save"][1] == "Chat"


def test_persist_chat_session_updates_when_existing():
    db = type("DB", (), {})()
    calls = {}

    def update_chat_session(session_id, messages_json, context_data=None):
        calls["update"] = (session_id, messages_json, context_data)

    db.save_chat_session = lambda *args, **kwargs: 1
    db.update_chat_session = update_chat_session

    panel = _Panel()
    panel._notebooks = [2]

    session_id = persist_chat_session(db, 99, [{"role": "assistant", "content": "Done"}], panel, {7})

    assert session_id == 99
    assert calls["update"][0] == 99
