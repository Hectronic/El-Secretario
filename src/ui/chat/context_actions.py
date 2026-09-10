"""Chat-context application policy separated from the chat widget shell."""

from PyQt6.QtCore import Qt

from src.ui.chat.context_state import parse_chat_context_state


def apply_initial_contexts(widget, contexts):
    widget.context_panel.reset_all()
    parsed = parse_chat_context_state(contexts)
    widget.context_panel.current_week_monday = parsed["current_week_monday"]
    widget.context_panel.current_date_filter = parsed["current_date_filter"]
    widget.context_panel.active_global_tags = list(parsed["active_global_tags"])
    widget.forced_record_ids = set(parsed["forced_record_ids"])
    widget.forced_record_labels = list(parsed["forced_record_labels"])
    for index in range(widget.context_panel.nb_list.count()):
        item = widget.context_panel.nb_list.item(index)
        item.setCheckState(Qt.CheckState.Checked if item.data(Qt.ItemDataRole.UserRole) in parsed["notebook_ids"] else Qt.CheckState.Unchecked)
    if parsed["has_recording_context"]:
        widget.context_panel.sync_cb.setChecked(False)
    forced_records = []
    for record_id in sorted(widget.forced_record_ids):
        record = widget.db.fetch_record(record_id)
        if not isinstance(record, dict):
            record = {}
        forced_records.append({
            "id": record_id,
            "title": record.get("title") or f"Recording {record_id}",
            "created_at": record.get("created_at") or "",
        })
    widget.context_panel.set_forced_records(forced_records)
    widget._refresh_title()
