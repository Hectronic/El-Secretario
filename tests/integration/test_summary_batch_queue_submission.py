from unittest.mock import MagicMock

from src.database import DBManager
from src.ui.summary_batch_widget import SummaryBatchWidget


def test_summary_batch_enqueues_missing_recording_from_injected_sqlite(qtbot, tmp_path, monkeypatch):
    db = DBManager(str(tmp_path / "summary-batch.sqlite"))
    record_id = db.save("meeting.wav", "Decision made", 5.0, "Meeting", recording_notes="Owner assigned")
    queue = MagicMock()
    queue.enqueue_recording_summary.return_value = True
    monkeypatch.setattr("src.ui.summary_batch_widget.QMessageBox.information", lambda *_args: None)
    widget = SummaryBatchWidget(task_queue=queue, persistence=db)
    qtbot.addWidget(widget)
    widget.chk_daily.setChecked(False)
    widget.chk_weekly.setChecked(False)

    widget.start_processing()

    queue.enqueue_recording_summary.assert_called_once()
    args, kwargs = queue.enqueue_recording_summary.call_args
    assert args[0] == record_id
    assert "Decision made" in args[1]
    assert kwargs["source"] == "batch_summary"
