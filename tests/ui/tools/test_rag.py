from src.ui.tools.rag import queue_rag_reindex


class _Queue:
    def __init__(self, accepted):
        self.accepted = accepted
        self.calls = []

    def enqueue_rag_reindex(self, **kwargs):
        self.calls.append(kwargs)
        return self.accepted


def test_rag_queue_policy_reports_queue_availability_and_deduplication():
    assert queue_rag_reindex(None, "all") == (False, "Task queue is not available.", "error")
    queue = _Queue(True)
    assert queue_rag_reindex(queue, "missing") == (True, "✓ RAG reindex task queued (missing records only).", "success")
    assert queue.calls == [{"scope": "missing", "source": "tools"}]
    assert queue_rag_reindex(_Queue(False), "all")[2] == "warning"
