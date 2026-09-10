"""Pure batch queue lifecycle state."""

BATCH_TASK_TYPES = {"transcription", "summary", "task_extraction"}


def is_batch_task(task):
    return task.get("source") == "batch_process" and task.get("type") in BATCH_TASK_TYPES


def batch_task_token(task):
    return tuple(task.get(key) for key in ("type", "record_id", "date", "title", "source"))


class BatchQueueState:
    def __init__(self):
        self.reset()

    def reset(self, record_ids=()):
        self.queued_record_ids = set(record_ids)
        self.active_tasks = 0
        self.handled_terminal_tasks = set()
        self.processed_count = 0

    def register_enqueued(self, task):
        if not is_batch_task(task):
            return False
        self.active_tasks += 1
        return True

    def register_terminal(self, task):
        if not is_batch_task(task):
            return False
        token = batch_task_token(task)
        if token in self.handled_terminal_tasks:
            return False
        self.handled_terminal_tasks.add(token)
        self.active_tasks = max(0, self.active_tasks - 1)
        return True

    def register_transcription_terminal(self, task):
        record_id = task.get("record_id")
        if task.get("type") != "transcription" or record_id not in self.queued_record_ids:
            return False
        self.queued_record_ids.remove(record_id)
        self.processed_count += 1
        return True
