from unittest.mock import MagicMock

from src.database import DBManager
from src.ui.note_widget import NoteWidget
from src.ui.summary_batch_widget import SummaryBatchWidget
from src.ui.task_batch_widget import TaskBatchWidget


def test_note_widget_persists_a_note_through_the_injected_sqlite_port(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "notes.sqlite"))
    widget = NoteWidget(rag_engine=None, persistence=db)
    qtbot.addWidget(widget)

    widget.title_input.setText("Integration note")
    widget.content_editor.setPlainText("Persisted through the injected port")
    widget.tags_input.setText("integration")
    widget.save_note()

    record = db.fetch_record(widget.current_record_id)
    assert record["type"] == "note"
    assert record["title"] == "Integration note"
    assert record["transcription"] == "Persisted through the injected port"
    assert record["tags"] == "integration"


def test_batch_widgets_query_the_same_injected_sqlite_port(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "batch.sqlite"))
    db.save("meeting.wav", "Transcript", 10.0, "Meeting")
    queue = MagicMock()
    summary_widget = SummaryBatchWidget(task_queue=queue, persistence=db)
    task_widget = TaskBatchWidget(task_queue=queue, persistence=db)
    qtbot.addWidget(summary_widget)
    qtbot.addWidget(task_widget)

    summary_widget.refresh_stats()
    task_widget.refresh_stats()

    assert summary_widget.db is db
    assert task_widget.db is db
    assert "1" in summary_widget.stats_label.text()
    assert task_widget.pending_records[0]["title"] == "Meeting"
