from unittest.mock import MagicMock

from src.database import DBManager
from src.notebook_database import NotebookDBManager
from src.ui.tools_widget import ToolsWidget


def test_tools_widget_shares_injected_sqlite_port_with_all_batch_tabs_and_rag(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "tools.sqlite"))
    notebook_db = NotebookDBManager(str(tmp_path / "notebooks.sqlite"))
    queue = MagicMock()
    queue.enqueue_rag_reindex.return_value = True
    widget = ToolsWidget(db, notebook_db, task_queue=queue)
    qtbot.addWidget(widget)

    assert widget.processing_widget.db is db
    assert widget.summary_widget.db is db
    assert widget.tasks_batch_widget.db is db

    widget._queue_rag_reindex()
    queue.enqueue_rag_reindex.assert_called_once_with(scope="all", source="tools")
    assert "queued" in widget.rag_status_lbl.text()
