from unittest.mock import MagicMock

from src.database import DBManager
from src.ui.chat_widget import ChatWidget


def _notebook_port():
    port = MagicMock()
    port.get_notebooks.return_value = []
    port.get_entries.return_value = []
    return port


def test_chat_response_persists_and_restores_session_with_real_sqlite(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "chat.sqlite"))
    notebook_db = _notebook_port()
    rag = MagicMock()
    rag.search.return_value = []
    widget = ChatWidget(
        rag,
        initial_contexts=[{"type": "tag", "value": "planning", "label": "planning"}],
        persistence=db,
        notebook_persistence=notebook_db,
    )
    qtbot.addWidget(widget)

    widget.chat_history.append({"role": "user", "content": "What is next?"})
    widget.on_chat_finished("Ship the integration tests.")

    session_id = widget.current_session_id
    session = next(item for item in db.fetch_chat_sessions() if item["id"] == session_id)
    assert "Ship the integration tests." in session["messages"]

    restored = ChatWidget(
        rag,
        session_id=session_id,
        persistence=db,
        notebook_persistence=notebook_db,
    )
    qtbot.addWidget(restored)

    assert restored.chat_history == widget.chat_history
    assert restored.context_panel.active_global_tags == ["planning"]
