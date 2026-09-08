"""Context-entry query and presentation descriptors."""


def fetch_context_records(db, state):
    tags = state.tags or None
    if state.week_monday:
        return db.fetch_by_date_range(
            state.week_monday.toString("yyyy-MM-dd"), state.date_filter, tags
        )
    if state.date_filter:
        return db.fetch_by_dates([state.date_filter], tags)
    if state.tags:
        return db.fetch_by_date_range("1970-01-01", "2099-12-31", state.tags)
    return []


def entry_descriptors(forced_records, records, notebook_entries):
    descriptors = []
    seen_record_ids = set()
    for record in forced_records:
        record_id = record.get("id")
        if record_id is not None:
            seen_record_ids.add(int(record_id))
        descriptors.append((f"📌 🎤 {record.get('title') or 'Untitled'}", record.get("created_at") or ""))
    for record in records:
        record_id = record.get("id")
        if record_id is not None and int(record_id) in seen_record_ids:
            continue
        if record_id is not None:
            seen_record_ids.add(int(record_id))
        icon = "🎤" if record.get("type") == "recording" else "📝"
        descriptors.append((f"{icon} {record.get('title') or 'Untitled'}", str(record.get("created_at") or "")))
    for entry in notebook_entries:
        descriptors.append((f"📓 {entry.get('title') or 'Notebook note'}", ""))
    return descriptors
