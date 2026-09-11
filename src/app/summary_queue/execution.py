"""Worker-outcome orchestration for the sequential summary queue."""

import logging
from uuid import uuid4

from src.app.summary_queue.runtime import build_retry_wait_state, cleanup_between_jobs
from src.worker_components.lifecycle import TerminalOutcome, TerminalStatus


class QueueWorkerExecutionCoordinator:
    """Apply worker signals to queue state without owning the Qt queue facade."""

    def __init__(
        self,
        *,
        state,
        history,
        wait_state,
        wait_timer,
        completion_actions,
        handle_completion,
        append_history,
        emit_progress,
        emit_status,
        emit_skipped,
        emit_failed,
        emit_finished,
        emit_wait_state,
        emit_queue_state,
        start_next,
        retain_worker,
        is_fatal_transcription_failure,
        emit_terminal=lambda _outcome: None,
    ):
        self.state = state
        self.history = history
        self.wait_state = wait_state
        self.wait_timer = wait_timer
        self.completion_actions = completion_actions
        self.handle_completion = handle_completion
        self.append_history = append_history
        self.emit_progress = emit_progress
        self.emit_status = emit_status
        self.emit_skipped = emit_skipped
        self.emit_failed = emit_failed
        self.emit_finished = emit_finished
        self.emit_wait_state = emit_wait_state
        self.emit_queue_state = emit_queue_state
        self.start_next = start_next
        self.retain_worker = retain_worker
        self.is_fatal_transcription_failure = is_fatal_transcription_failure
        self.emit_terminal = emit_terminal
        self._terminal_task_ids = set()

    def _emit_terminal_once(self, task, status, *, message="", retryable=False):
        task_id = id(task)
        if task_id in self._terminal_task_ids:
            return
        self._terminal_task_ids.add(task_id)
        outcome = TerminalOutcome(
            status=TerminalStatus(status),
            operation_id=task.get("_operation_id") or uuid4().hex,
            user_message=message,
            retryable=retryable,
            preserved_work=True,
        )
        self.emit_terminal(outcome.payload())

    def on_generator_progress(self, current, total):
        if total > 0:
            self.emit_progress(int((current / total) * 100))

    def on_generator_recording_summary_completed(self, record_id, title):
        try:
            self.completion_actions().enqueue_tasks_for_completed_recording(
                record_id,
                title,
                current_task=self.state.current_task,
            )
        except Exception:
            logging.exception("Queue: failed to enqueue post-summary task extraction.")

    def on_worker_completed(self, result=None):
        task = self.state.current_task or {}
        if result is None:
            logging.debug("Queue: worker completed without result for task type=%s.", task.get("type"))
            return

        try:
            logging.info("Queue: applying completion actions for task type=%s.", task.get("type"))
            self.completion_actions().apply(self.handle_completion(task, result))
        except Exception:
            logging.exception("Queue: persistence error for task type=%s.", task.get("type"))

    def on_worker_error(self, error_msg):
        task = self.state.current_task or {}
        self.clear_wait_state()
        self.state.current_task_had_error = True
        message = str(error_msg or "Unknown error")
        if task.get("type") == "transcription" and self.is_fatal_transcription_failure(message):
            self.append_history("skipped", task, message)
            self.emit_skipped(task, message)
            self._emit_terminal_once(task, TerminalStatus.FAILED, message=message, retryable=True)
            self.emit_status(f"Skipping failed transcription: {message}")
            logging.warning("Queue: fatal transcription failure converted to skipped: %s", message)
            return

        self.append_history("failed", task, message)
        self.emit_failed(task, message)
        self._emit_terminal_once(task, TerminalStatus.FAILED, message=message, retryable=True)
        logging.error("Queue: task failed type=%s error=%s", task.get("type"), message)

    def on_worker_status_update(self, message):
        msg = str(message or "").strip()
        if not msg:
            return
        self.emit_status(msg)
        current_task = self.state.current_task or {}
        if current_task:
            self.history.append_status_trace_once(current_task, msg)

    def on_worker_completely_finished(self):
        had_error = self.state.current_task_had_error
        task, worker = self.state.finish_current()
        self.history.clear_status_dedup()
        self.clear_wait_state()
        if task:
            if not had_error:
                self.append_history("finished", task)
                logging.info("Queue: task finished successfully type=%s.", task.get("type"))
                self.emit_finished(task)
                self._emit_terminal_once(task, TerminalStatus.SUCCEEDED)
        if worker:
            worker.deleteLater()
            self.retain_worker(worker)
        cleanup_between_jobs()
        self.emit_queue_state()
        self.start_next()

    def on_worker_retry_wait(self, delay_seconds, attempt, total_attempts, error_text):
        wait, description, status_message = build_retry_wait_state(
            delay_seconds,
            attempt,
            total_attempts,
            error_text,
        )
        self.wait_state.begin(wait, description)
        self.emit_wait_state(*self.wait_state.snapshot())
        if not self.wait_timer.isActive():
            self.wait_timer.start()
        self.emit_status(status_message)
        logging.info("Queue: retry wait state set (%ss) for attempt %s/%s.", wait, attempt + 1, total_attempts)

    def tick_wait_state(self):
        if not self.wait_state.tick():
            self.clear_wait_state()
            return
        self.emit_wait_state(*self.wait_state.snapshot())

    def clear_wait_state(self):
        self.wait_state.clear()
        if self.wait_timer.isActive():
            self.wait_timer.stop()
        self.emit_wait_state(False, 0, "")
