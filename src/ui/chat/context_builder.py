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

"""Helpers that assemble chat context text and session metadata."""

import logging


def build_chat_context_text(db, notebook_db, rag, query, context_panel, forced_record_ids):
    context_text_parts = []

    notebook_ids = context_panel.get_active_notebooks()
    for nid in notebook_ids:
        entries = notebook_db.get_entries(nid)
        for entry in entries:
            content = entry["content"]
            title = entry["title"] or "Untitled"
            context_text_parts.append(f"[Notebook note: {title}]\n{content}")

    tags = context_panel.get_active_tags()
    records = []
    seen_ids = set()

    for rid in sorted(forced_record_ids):
        rec = db.fetch_record(rid)
        if isinstance(rec, dict) and rec.get("id") is not None:
            records.append(rec)
            seen_ids.add(int(rec["id"]))

    if context_panel.current_week_monday:
        start_date = context_panel.current_week_monday.toString("yyyy-MM-dd")
        end_date = context_panel.current_date_filter
        for rec in db.fetch_by_date_range(start_date, end_date, tags if tags else None):
            rid = int(rec.get("id"))
            if rid not in seen_ids:
                seen_ids.add(rid)
                records.append(rec)
    elif context_panel.current_date_filter:
        for rec in db.fetch_by_dates([context_panel.current_date_filter], tags if tags else None):
            rid = int(rec.get("id"))
            if rid not in seen_ids:
                seen_ids.add(rid)
                records.append(rec)
    elif tags:
        for rec in db.fetch_by_date_range("1970-01-01", "2099-12-31", tags):
            rid = int(rec.get("id"))
            if rid not in seen_ids:
                seen_ids.add(rid)
                records.append(rec)

    tasks = []
    if context_panel.current_week_monday:
        start_date = context_panel.current_week_monday.toString("yyyy-MM-dd")
        end_date = context_panel.current_date_filter
        tasks = db.get_tasks_by_date_range(start_date, end_date, ",".join(tags) if tags else None)
    elif context_panel.current_date_filter:
        tasks = db.get_tasks_by_date(context_panel.current_date_filter, ",".join(tags) if tags else None)
    elif tags:
        tasks = db.get_tasks_by_date_range("1970-01-01", "2099-12-31", ",".join(tags))

    rag_ids = None
    if records:
        rag_ids = [str(r["id"]) for r in records]
        for r in records:
            composed = db.compose_ai_text(r.get("transcription"), r.get("recording_notes"))
            record_label = "Meeting" if r.get("type") == "recording" else "Note"
            context_text_parts.append(
                f"[{record_label}: {r['title'] or 'Untitled'} ({r['created_at']})]\n{composed}"
            )

    if tasks:
        task_lines = []
        for task in tasks:
            status = "done" if task.get("is_completed") else "pending"
            origin = (task.get("task_origin") or task.get("record_title") or "").strip()
            origin_suffix = f" [{origin}]" if origin else ""
            task_lines.append(f"- ({status}) {(task.get('content') or '').strip()}{origin_suffix}")
        context_text_parts.append("[Tasks]\n" + "\n".join(task_lines))

    if rag_ids or (not tags and not context_panel.current_date_filter):
        try:
            results = rag.search(query, n_results=5, ids=rag_ids)
            for r in results:
                context_text_parts.append(
                    f"[Fragmento relevante: {r['metadata'].get('title', 'Desconocido')}]\n{r['text']}"
                )
        except Exception:
            logging.exception("RAG search failed while building chat context")

    context_text = "\n\n".join(context_text_parts)
    if not context_text:
        context_text = "No relevant context found."

    return context_text


def build_chat_session_contexts(context_panel, forced_record_ids):
    save_contexts = []
    if context_panel.current_week_monday and context_panel.current_date_filter:
        save_contexts.append(
            {
                "type": "date_range",
                "value": {
                    "start": context_panel.current_week_monday.toString("yyyy-MM-dd"),
                    "end": context_panel.current_date_filter,
                },
            }
        )
    elif context_panel.current_date_filter:
        save_contexts.append({"type": "date", "value": context_panel.current_date_filter})

    for tag in context_panel.get_active_tags():
        save_contexts.append({"type": "tag", "value": tag})
    for notebook_id in context_panel.get_active_notebooks():
        save_contexts.append({"type": "notebook", "value": notebook_id})
    for rid in sorted(forced_record_ids):
        save_contexts.append({"type": "recording", "value": rid})

    return save_contexts
