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

"""Helpers for loading stored chat sessions into UI state."""

import json


def load_chat_session_state(session):
    """Extract chat history and stored contexts from a DB session row."""
    if not session:
        return {"messages": [], "contexts": None, "title": None, "session_id": None}

    messages_raw = session.get("messages") or "[]"
    try:
        messages = json.loads(messages_raw)
    except Exception:
        messages = []
    if not isinstance(messages, list):
        messages = []
    messages = [
        _normalize_message(message)
        for message in messages if isinstance(message, dict)
    ]

    contexts = None
    context_data = session.get("context_data")
    if context_data:
        try:
            contexts = json.loads(context_data)
        except Exception:
            contexts = None

    return {
        "messages": messages,
        "contexts": contexts,
        "title": session.get("name"),
        "session_id": session.get("id"),
    }


def _normalize_message(message):
    normalized = {
        "role": message.get("role") if message.get("role") in ("user", "assistant") else "assistant",
        "content": str(message.get("content") or ""),
    }
    if message.get("role") == "assistant" and ("sources" in message or "retrieval_degraded" in message):
        normalized["sources"] = [
            {
                "source_id": str(source.get("source_id")),
                "title": str(source.get("title") or f"Fuente {source.get('source_id')}"),
                "excerpt": str(source.get("excerpt") or "")[:600],
                "role": str(source.get("role") or "Fuente"),
                "degraded": bool(source.get("degraded")),
            }
            for source in (message.get("sources") or [])
            if isinstance(source, dict) and source.get("source_id") is not None
        ]
        normalized["retrieval_degraded"] = bool(message.get("retrieval_degraded"))
    return normalized
