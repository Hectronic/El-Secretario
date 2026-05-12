# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <https://www.gnu.org/licenses/>.

class _Display:
    def __init__(self):
        self.cleared = False

    def clear(self):
        self.cleared = True


class _Widget:
    def __init__(self):
        self.current_session_id = None
        self.chat_history = []
        self.display = _Display()
        self.appended = []
        self.applied_contexts = None
        self.refreshed_title = None

    def _apply_contexts(self, contexts):
        self.applied_contexts = contexts

    def append_to_chat(self, role, content):
        self.appended.append((role, content))

    def _refresh_title(self, title):
        self.refreshed_title = title


def test_apply_loaded_chat_session_replays_state():
    from src.ui.chat.session_applier import apply_loaded_chat_session

    widget = _Widget()
    loaded = {
        "session_id": 44,
        "messages": [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi"}],
        "contexts": [{"type": "tag", "value": "ops"}],
        "title": "Session Title",
    }

    apply_loaded_chat_session(widget, loaded)

    assert widget.current_session_id == 44
    assert widget.chat_history == loaded["messages"]
    assert widget.display.cleared is True
    assert widget.appended == [("User", "Hello"), ("Assistant", "Hi")]
    assert widget.applied_contexts == loaded["contexts"]
    assert widget.refreshed_title == "Session Title"
