# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.

from src.ui.chat.session_loader import load_chat_session_state


def test_load_chat_session_state_parses_messages_and_contexts():
    session = {
        "id": 12,
        "name": "Session",
        "messages": '[{"role":"user","content":"Hello"}]',
        "context_data": '[{"type":"tag","value":"ops"}]',
    }

    loaded = load_chat_session_state(session)

    assert loaded["session_id"] == 12
    assert loaded["title"] == "Session"
    assert loaded["messages"][0]["content"] == "Hello"
    assert loaded["contexts"][0]["type"] == "tag"


def test_load_chat_session_state_handles_invalid_json():
    session = {"id": 99, "messages": "not-json", "context_data": "bad"}

    loaded = load_chat_session_state(session)

    assert loaded["session_id"] == 99
    assert loaded["messages"] == []
    assert loaded["contexts"] is None


def test_load_chat_session_state_preserves_new_source_metadata_and_ignores_malformed_values():
    session = {
        "id": 7,
        "messages": '[{"role":"assistant","content":"Answer","sources":[{"source_id":"2"}],"retrieval_degraded":true},{"role":"assistant","content":"Old","sources":null}]',
    }

    loaded = load_chat_session_state(session)

    assert loaded["messages"][0]["sources"] == [{
        "source_id": "2", "title": "Fuente 2", "excerpt": "", "role": "Fuente", "degraded": False,
    }]
    assert loaded["messages"][0]["retrieval_degraded"] is True
    assert loaded["messages"][1] == {"role": "assistant", "content": "Old", "sources": [], "retrieval_degraded": False}
