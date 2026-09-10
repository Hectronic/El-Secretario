import json
from unittest.mock import MagicMock

from src.ui.chat.window_state import (
    build_window_context,
    load_window_session,
    save_window_session,
)


def test_build_window_context_scopes_search_to_selected_collection():
    rag = MagicMock()
    rag.search.return_value = [{"text": "Plan the release"}, {"text": "Write tests"}]

    context = build_window_context(rag, "What is next?", "planning")

    assert context == "Note: Plan the release\n\nNote: Write tests"
    rag.search.assert_called_once_with("What is next?", n_results=5, tag_filter="planning")


def test_build_window_context_explains_empty_search_result():
    rag = MagicMock(search=MagicMock(return_value=[]))

    assert build_window_context(rag, "What is next?", "All") == "No relevant notes found for this query."


def test_load_window_session_returns_only_requested_session():
    persistence = MagicMock()
    persistence.fetch_chat_sessions.return_value = [{"id": 1}, {"id": 2}]

    assert load_window_session(persistence, 2) == {"id": 2}
    assert load_window_session(persistence, 3) is None


def test_save_window_session_creates_then_updates_with_serialized_history():
    persistence = MagicMock()
    persistence.save_chat_session.return_value = 42
    history = [{"role": "user", "content": "A focused question"}]

    created_id = save_window_session(persistence, None, history, "planning")
    updated_id = save_window_session(persistence, created_id, history, "planning")

    assert created_id == updated_id == 42
    persistence.save_chat_session.assert_called_once_with(
        "A focused question...", "planning", json.dumps(history)
    )
    persistence.update_chat_session.assert_called_once_with(42, json.dumps(history))
