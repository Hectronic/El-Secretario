"""Summary-scoped date, tag, and chat-context policy."""

from PyQt6.QtCore import QDate


def summary_tags(summary_data):
    tags_filter = summary_data.get("tags_filter")
    return [tag.strip() for tag in str(tags_filter).split(",") if tag.strip()] if tags_filter else None


def summary_date_range(summary_data):
    if summary_data.get("type", "daily") == "daily":
        date_str = summary_data.get("date")
        return date_str, date_str
    sunday_str = summary_data.get("week_start")
    if not sunday_str:
        return None, None
    sunday = QDate.fromString(sunday_str, "yyyy-MM-dd")
    return sunday.addDays(-6).toString("yyyy-MM-dd"), sunday_str


def build_week_chat_contexts(summary_data, db):
    start, end = summary_date_range(summary_data)
    if not start or not end:
        return []
    tags = summary_tags(summary_data)
    contexts = [{"type": "date_range", "value": {"start": start, "end": end}, "label": f"{start} to {end}"}]
    contexts.extend({"type": "tag", "value": tag, "label": tag} for tag in tags or [])
    if db:
        for record in db.fetch_by_date_range(start, end, tags=tags):
            record_id = record.get("id")
            if isinstance(record_id, int):
                contexts.append({"type": "recording", "value": record_id, "label": (record.get("title") or f"Recording {record_id}").strip()})
    return contexts
