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

"""Parsing helpers for stored chat context data."""

from PyQt6.QtCore import QDate


def parse_chat_context_state(contexts):
    """Normalize stored chat contexts into a UI-friendly state dictionary."""
    state = {
        "current_week_monday": None,
        "current_date_filter": None,
        "active_global_tags": [],
        "notebook_ids": [],
        "forced_record_ids": set(),
        "forced_record_labels": [],
        "has_recording_context": False,
    }

    for ctx in contexts or []:
        ctx_type = (ctx or {}).get("type")
        ctx_value = (ctx or {}).get("value")
        if ctx_type == "date" and ctx_value:
            state["current_date_filter"] = str(ctx_value)
        elif ctx_type == "date_range" and isinstance(ctx_value, dict):
            start = str(ctx_value.get("start") or "").strip()
            end = str(ctx_value.get("end") or "").strip()
            start_date = QDate.fromString(start, "yyyy-MM-dd")
            if start_date.isValid() and end:
                state["current_week_monday"] = start_date
                state["current_date_filter"] = end
        elif ctx_type == "tag" and ctx_value:
            tag_value = str(ctx_value).strip()
            if tag_value and tag_value not in state["active_global_tags"]:
                state["active_global_tags"].append(tag_value)
        elif ctx_type == "notebook" and ctx_value is not None:
            state["notebook_ids"].append(ctx_value)
        elif ctx_type == "recording":
            state["has_recording_context"] = True
            try:
                rid = int(ctx_value)
            except (TypeError, ValueError):
                continue
            state["forced_record_ids"].add(rid)
            label = ((ctx or {}).get("label") or f"Recording {rid}").strip()
            if label and label not in state["forced_record_labels"]:
                state["forced_record_labels"].append(label)

    return state
