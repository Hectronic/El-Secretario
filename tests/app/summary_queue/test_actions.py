from src.app.summary_queue.actions import QueueActionCoordinator


class _QueueStub:
    def __init__(self):
        self._pending = ["a", "b", "c"]
        self._running = True
        self.cancel_current_called = 0
        self.cancel_all_called = 0

    @property
    def pending_count(self):
        return len(self._pending) + (1 if self._running else 0)

    @property
    def is_running(self):
        return self._running

    def move_task(self, from_index: int, to_index: int) -> bool:
        if from_index < 0 or to_index < 0:
            return False
        if from_index >= len(self._pending) or to_index >= len(self._pending):
            return False
        task = self._pending.pop(from_index)
        self._pending.insert(to_index, task)
        return True

    def remove_task_at(self, index: int) -> bool:
        if 0 <= index < len(self._pending):
            del self._pending[index]
            return True
        return False

    def cancel_current(self) -> bool:
        self.cancel_current_called += 1
        self._running = False
        return True

    def cancel_all(self) -> None:
        self.cancel_all_called += 1
        self._pending = []
        self._running = False


def test_actions_move_up_and_down():
    queue = _QueueStub()
    actions = QueueActionCoordinator(queue)

    assert actions.move_up(0) == 0
    assert actions.move_up(1) == 0
    assert queue._pending == ["b", "a", "c"]

    assert actions.move_down(0, 3) == 1
    assert queue._pending == ["a", "b", "c"]
    assert actions.move_down(2, 3) == 2


def test_actions_remove_selected_and_clear_pending():
    queue = _QueueStub()
    actions = QueueActionCoordinator(queue)

    assert actions.remove_selected(-1) is False
    assert actions.remove_selected(1) is True
    assert queue._pending == ["a", "c"]

    removed = actions.clear_pending()
    assert removed == 2
    assert queue._pending == []


def test_actions_stop_current_and_stop_all():
    queue = _QueueStub()
    actions = QueueActionCoordinator(queue)

    assert actions.stop_current() is True
    assert queue.cancel_current_called == 1
    assert queue.is_running is False

    actions.stop_all()
    assert queue.cancel_all_called == 1
