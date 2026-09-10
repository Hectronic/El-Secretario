"""Qt worker construction and startup for the sequential summary queue."""

import logging

from PyQt6.QtCore import QSettings

from src.app.summary_queue.worker_factory import build_queue_worker
from src.app.summary_queue.worker_lifecycle import start_queue_worker_lifecycle
from src.app.summary_queue.worker_signals import connect_queue_worker_signals
from src.app.summary_queue.threads import RAGReindexThread
from src.ai_assistant import AIAssistant
from src.summary_generator import SummaryGenerator
from src.worker_components.transcriber_thread import TranscriberThread


def start_next_worker_if_idle(
    *,
    state,
    parent,
    db,
    rag_engine,
    clear_wait_state,
    on_worker_completed,
    on_generator_recording_summary_completed,
    on_generator_progress,
    emit_progress,
    on_status_update,
    on_error,
    on_finished,
    on_retry_wait,
    set_current_worker,
    emit_task_started,
    append_history,
    emit_queue_state,
) -> bool:
    """Start one worker when idle, returning whether a task was started."""
    if state.current_worker is not None:
        logging.debug("Queue: start skipped because a worker is already running.")
        return False
    if not state.pending:
        logging.debug("Queue: start skipped because pending queue is empty.")
        emit_queue_state()
        return False

    task = state.take_next()
    if task is None:
        return False
    clear_wait_state()
    task_type = task["type"]
    logging.info("Queue: starting task type=%s.", task_type)

    try:
        worker = build_queue_worker(
            task,
            parent=parent,
            db=db,
            rag_engine=rag_engine,
            on_worker_completed=on_worker_completed,
            on_generator_recording_summary_completed=on_generator_recording_summary_completed,
            on_generator_progress=on_generator_progress,
            on_progress_emit=emit_progress,
            on_status_update=on_status_update,
            settings_cls=QSettings,
            summary_generator_cls=SummaryGenerator,
            transcriber_cls=TranscriberThread,
            rag_reindex_thread_cls=RAGReindexThread,
            ai_assistant_cls=AIAssistant,
        )
        connect_queue_worker_signals(
            worker,
            task_type=task_type,
            on_error=on_error,
            on_finished=on_finished,
            on_status_update=on_status_update,
            on_retry_wait=on_retry_wait,
        )
        start_queue_worker_lifecycle(
            worker=worker,
            task=task,
            pending_remaining=len(state.pending),
            set_current_worker=set_current_worker,
            emit_task_started=emit_task_started,
            append_history=append_history,
            emit_queue_state=emit_queue_state,
        )
        return True
    except Exception as error:
        logging.error(
            "Queue: failed to start worker for task type=%s: %s",
            task_type,
            error,
            exc_info=True,
        )
        on_error(str(error))
        return False
