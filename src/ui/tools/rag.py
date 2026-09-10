"""RAG queue request policy for the Tools tab."""


def queue_rag_reindex(task_queue, scope):
    if task_queue is None:
        return False, "Task queue is not available.", "error"
    scope = scope or "all"
    queued = task_queue.enqueue_rag_reindex(scope=scope, source="tools")
    if queued:
        scope_text = "all records" if scope == "all" else "missing records only"
        return True, f"✓ RAG reindex task queued ({scope_text}).", "success"
    return False, "RAG reindex task with this scope is already running or queued.", "warning"
