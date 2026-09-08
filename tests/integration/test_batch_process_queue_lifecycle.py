from PyQt6.QtCore import QObject, pyqtSignal

from src.database import DBManager
from src.ui.batch_process_widget import BatchProcessWidget


class _Queue(QObject):
    task_enqueued = pyqtSignal(dict, int)
    task_started = pyqtSignal(dict, int)
    task_finished = pyqtSignal(dict)
    task_failed = pyqtSignal(dict, str)
    task_skipped = pyqtSignal(dict, str)

    def __init__(self):
        super().__init__()
        self.requests = []

    def enqueue_transcription(self, record_id, file_path, **kwargs):
        task = {"type": "transcription", "record_id": record_id, **kwargs}
        self.requests.append((file_path, task))
        self.task_enqueued.emit(task, len(self.requests))
        return True


def test_batch_process_uses_injected_sqlite_and_real_queue_signals(qtbot, tmp_path, monkeypatch):
    db = DBManager(str(tmp_path / "batch-process.sqlite"))
    record_id = db.save("pending.wav", "", 4.0, "Pending recording")
    queue = _Queue()
    monkeypatch.setattr("src.ui.batch_process_widget.QMessageBox.information", lambda *_args: None)
    widget = BatchProcessWidget(task_queue=queue, persistence=db)
    qtbot.addWidget(widget)

    assert widget.pending_list.count() == 1
    widget.start_processing()

    assert len(queue.requests) == 1
    _file_path, task = queue.requests[0]
    assert task["record_id"] == record_id
    assert task["source"] == "batch_process"
    queue.task_started.emit(task, 0)
    queue.task_finished.emit(task)

    assert widget.processed_count == 1
    assert widget.status_label.text() == "Batch processing finished."
    assert widget.progress_bar.value() == 100
