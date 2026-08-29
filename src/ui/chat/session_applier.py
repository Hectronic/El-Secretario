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

"""Apply loaded chat session state to a widget."""


def apply_loaded_chat_session(widget, loaded_session):
    widget.current_session_id = loaded_session["session_id"]
    widget.chat_history = loaded_session["messages"]

    contexts = loaded_session.get("contexts")
    if contexts:
        widget._apply_contexts(contexts)

    widget.display.clear()
    for msg in widget.chat_history:
        role_name = "User" if msg["role"] == "user" else "Assistant"
        widget.append_to_chat(role_name, msg["content"])
    widget._refresh_title(loaded_session["title"])
