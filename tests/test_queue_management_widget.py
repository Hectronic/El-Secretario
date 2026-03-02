from PyQt6.QtCore import QObject, pyqtSignal

from src.ui.queue_management_widget import QueueManagementWidget


class _FakeQueue(QObject):
    queue_changed = pyqtSignal(int, bool)
    task_started = pyqtSignal(dict, int)
    task_finished = pyqtSignal(dict)
    wait_state_changed = pyqtSignal(bool, int, str)
    task_status_update = pyqtSignal(str)
    task_progress = pyqtSignal(int)
    task_failed = pyqtSignal(dict, str)
    task_skipped = pyqtSignal(dict, str)

    def __init__(self):
        super().__init__()
        self._current = {"type": "summary", "title": "Demo"}
        self._pending = []

    def get_current_task(self):
        return self._current

    def get_queue_list(self):
        return list(self._pending)

    def get_wait_state(self):
        return False, 0, ""

    @property
    def pending_count(self):
        return len(self._pending) + (1 if self._current else 0)

    @property
    def is_running(self):
        return self._current is not None

    def move_task(self, *_args):
        return False

    def remove_task_at(self, *_args):
        return False

    def cancel_current(self):
        self._current = None
        self.queue_changed.emit(self.pending_count, self.is_running)

    def cancel_all(self):
        self._pending = []
        self._current = None
        self.queue_changed.emit(self.pending_count, self.is_running)


def test_queue_widget_shows_live_status_with_empty_pending(qtbot):
    fake_queue = _FakeQueue()
    widget = QueueManagementWidget(fake_queue)
    qtbot.addWidget(widget)

    # Running task is visible even when pending queue is empty.
    assert widget.queue_list.count() == 0
    assert "Demo" in widget.current_task_label.text()

    # Live status/progress are shown via queue signals.
    fake_queue.task_status_update.emit("Transcribing...")
    assert "Transcribing..." in widget.live_status_label.text()

    fake_queue.task_progress.emit(42)
    assert widget.live_progress.value() == 42
    assert widget.live_progress.format() == "42%"
