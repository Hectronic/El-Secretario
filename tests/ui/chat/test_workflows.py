import json
from unittest.mock import MagicMock

from src.ui.chat.workflows import filter_chat_sessions, source_cards, starter_prompts


def test_starters_reflect_selected_records_and_never_send_automatically():
    suggestions = starter_prompts(["Planning"], ["planning"])

    assert any("reuniones seleccionadas" in item for item in suggestions)
    assert all(isinstance(item, str) for item in suggestions)


def test_session_search_checks_title_and_message_and_orders_ties_by_id():
    sessions = [
        {"id": 1, "name": "Alpha", "created_at": "2026-01-01", "messages": "[]"},
        {"id": 3, "name": "Other", "created_at": "2026-01-01", "messages": json.dumps([{"content": "needle"}])},
        {"id": 2, "name": "Needle title", "created_at": "2026-01-01", "messages": "broken"},
    ]

    assert [item["id"] for item in filter_chat_sessions(sessions, "NEEDLE")] == [3, 2]
    assert [item["id"] for item in filter_chat_sessions(sessions, "")] == [3, 2, 1]


def test_sources_only_include_stable_identity_and_mark_degraded_retrieval():
    results = [
        {"id": "7", "text": "Excerpt", "metadata": {"title": "Planning", "type": "recording"}, "retrieval_mode": "keyword_fallback"},
        {"id": "opaque-fragment", "text": "No identity", "metadata": {}, "retrieval_mode": "semantic"},
    ]

    cards = source_cards(results)

    assert cards == [{"source_id": "7", "title": "Planning", "excerpt": "Excerpt", "role": "recording", "degraded": True}]


def test_context_summary_uses_only_selected_context():
    from src.ui.chat.workflows import context_summary

    panel = MagicMock()
    panel.current_week_monday = None
    panel.current_date_filter = None
    panel.get_active_tags.return_value = ["planning"]
    panel.get_active_notebooks.return_value = []
    panel.nb_list.count.return_value = 0

    result = context_summary(panel, [])

    assert "planning" in result
    assert "Sin contexto" not in result
    panel.db.fetch_all.assert_not_called()
