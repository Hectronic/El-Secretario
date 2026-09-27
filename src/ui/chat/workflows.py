"""Pure presentation policies for the chat's common workflows."""

import json


def starter_prompts(record_labels=(), tags=(), has_date=False, has_notebooks=False):
    """Return suggestions that reflect only context already selected by the user."""
    if record_labels:
        return (
            "Resume las reuniones seleccionadas",
            "¿Qué decisiones se tomaron?",
            "Extrae las próximas acciones",
            "Compara las reuniones seleccionadas",
        )
    if tags or has_date or has_notebooks:
        return (
            "Resume el contexto seleccionado",
            "¿Qué decisiones aparecen?",
            "Extrae las próximas acciones",
        )
    return ("¿Qué puedo preguntar sobre mis notas?", "Resume el contexto seleccionado")


def context_summary(context_panel, forced_record_labels=()):
    """Describe active selectors without querying or exposing unselected records."""
    parts = []
    records = [str(label).strip() for label in forced_record_labels if str(label).strip()]
    if records:
        parts.append("Registros: " + ", ".join(records))
    if context_panel.current_week_monday:
        start = context_panel.current_week_monday.toString("yyyy-MM-dd")
        parts.append(f"Semana: {start} – {context_panel.current_date_filter or start}")
    elif context_panel.current_date_filter:
        parts.append(f"Fecha: {context_panel.current_date_filter}")
    tags = [str(tag).strip() for tag in context_panel.get_active_tags() if str(tag).strip()]
    if tags:
        parts.append("Etiquetas: " + ", ".join(tags))
    notebook_names = []
    for index in range(context_panel.nb_list.count()):
        item = context_panel.nb_list.item(index)
        if item.checkState().value == 2:
            notebook_names.append(item.text().removeprefix("📓 "))
    if notebook_names:
        parts.append("Cuadernos: " + ", ".join(notebook_names))
    if parts:
        parts.append("Tareas: mismo ámbito seleccionado")
    return " · ".join(parts) if parts else "Sin contexto adicional seleccionado"


def filter_chat_sessions(sessions, query):
    """Filter persisted session titles/messages locally in stable newest-first order."""
    needle = (query or "").strip().casefold()
    matches = []
    for session in sessions or ():
        if not isinstance(session, dict):
            continue
        try:
            messages = json.loads(session.get("messages") or "[]")
            if not isinstance(messages, list):
                messages = []
        except (TypeError, ValueError):
            messages = []
        body = " ".join(
            str(message.get("content") or "")
            for message in messages if isinstance(message, dict)
        )
        if not needle or needle in str(session.get("name") or "").casefold() or needle in body.casefold():
            matches.append(session)
    def stable_key(item):
        try:
            identifier = int(item.get("id") or 0)
        except (TypeError, ValueError):
            identifier = 0
        return str(item.get("created_at") or ""), identifier
    return sorted(matches, key=stable_key, reverse=True)


def source_cards(results):
    """Shape only explicit RAG provenance; missing identities stay unavailable."""
    cards = []
    for result in results or ():
        if not isinstance(result, dict):
            continue
        metadata = result.get("metadata") or {}
        source_id = metadata.get("source_id")
        if source_id is None:
            candidate = metadata.get("recording_id") or metadata.get("record_id") or result.get("id")
            if str(candidate or "").isdigit():
                source_id = candidate
        if source_id is None:
            continue
        cards.append({
            "source_id": str(source_id),
            "title": str(metadata.get("title") or f"Fuente {source_id}"),
            "excerpt": str(result.get("text") or "")[:600],
            "role": str(metadata.get("role") or metadata.get("type") or "Fuente"),
            "degraded": result.get("retrieval_mode") == "keyword_fallback",
        })
    return cards
