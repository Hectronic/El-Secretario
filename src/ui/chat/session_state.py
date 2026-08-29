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

"""Helpers for chat session naming and persistence payloads."""

import json

from src.ui.chat.context_builder import build_chat_session_contexts


def build_new_chat_session_name(chat_history):
    """Derive a reasonable name for a newly created chat session."""
    if chat_history:
        first_message = (chat_history[0].get("content") or "").strip()
        if first_message:
            return first_message[:30] + ("..." if len(first_message) > 30 else "")
    return "New Chat"


def resolve_chat_display_title(session_name, chat_history, forced_record_labels, active_tags, current_date_filter):
    """Resolve the visible title for a chat widget."""
    if session_name:
        return str(session_name).strip() or "New Chat"
    if chat_history:
        first_message = (chat_history[0].get("content") or "").strip()
        if first_message:
            return first_message[:30] + ("..." if len(first_message) > 30 else "")

    labels = list(forced_record_labels or [])
    labels.extend(active_tags or [])
    if current_date_filter:
        labels.append(current_date_filter)
    if labels:
        return ", ".join(labels[:2]) + ("..." if len(labels) > 2 else "")
    return "New Chat"


def build_chat_session_payload(chat_history, context_panel, forced_record_ids):
    """Build the JSON payloads used when saving or updating a chat session."""
    return {
        "messages_json": json.dumps(chat_history),
        "context_json": json.dumps(build_chat_session_contexts(context_panel, forced_record_ids)),
        "name": build_new_chat_session_name(chat_history),
    }


def persist_chat_session(db, current_session_id, chat_history, context_panel, forced_record_ids):
    """Create or update a chat session and return the final session id."""
    payload = build_chat_session_payload(chat_history, context_panel, forced_record_ids)
    if current_session_id:
        db.update_chat_session(
            current_session_id,
            payload["messages_json"],
            context_data=payload["context_json"],
        )
        return current_session_id

    return db.save_chat_session(
        payload["name"],
        "Chat",
        payload["messages_json"],
        context_data=payload["context_json"],
    )
