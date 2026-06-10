# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  See <https://www.gnu.org/licenses/>.

from unittest.mock import MagicMock

from src.ui.recording.ai_actions import (
    compose_record_ai_text,
    configure_legacy_ai_thread,
    enqueue_post_transcription_summary,
    enqueue_recording_summary,
    enqueue_task_extraction,
    extract_tasks_button_text,
    refresh_global_tasks_sidebar,
)


class Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, *args):
        for callback in list(self.callbacks):
            callback(*args)


class FakeAssistantThread:
    def __init__(self, prefix, task_type, text):
        self.prefix = prefix
        self.task_type = task_type
        self.text = text
        self.task_completed = Signal()
        self.error = Signal()
        self.finished = Signal()
        self.started = False

    def start(self):
        self.started = True


class FakeWidget:
    def __init__(self):
        self.status_changed = Signal()
        self.progress_changed = Signal()
        self.statuses = []
        self.progresses = []
        self.status_changed.connect(self.statuses.append)
        self.progress_changed.connect(self.progresses.append)
        self.on_ai_finished = MagicMock()
        self.on_ai_error = MagicMock()
        self._clear_ai_thread_ref = MagicMock()


def test_compose_record_ai_text_delegates_to_db():
    db = MagicMock()
    db.compose_ai_text.return_value = "Composed"

    assert compose_record_ai_text(db, "Transcript", "Notes") == "Composed"
    db.compose_ai_text.assert_called_once_with("Transcript", "Notes")


def test_extract_tasks_button_text_handles_existing_and_error_cases():
    db = MagicMock()
    db.has_ai_tasks_for_record.return_value = True
    assert extract_tasks_button_text(db, 7) == "Re-extract Tasks (AI)"

    db.has_ai_tasks_for_record.return_value = False
    assert extract_tasks_button_text(db, 7) == "Extract Tasks (AI)"

    db.has_ai_tasks_for_record.side_effect = RuntimeError("db")
    assert extract_tasks_button_text(db, 7) == "Extract Tasks (AI)"
    assert extract_tasks_button_text(db, None) == "Extract Tasks (AI)"


def test_enqueue_recording_summary_uses_recording_source():
    queue = MagicMock()
    enqueue_recording_summary(queue, 7, "Text", "Weekly")
    queue.enqueue_recording_summary.assert_called_once_with(7, "Text", "Weekly", source="recording")


def test_enqueue_task_extraction_deletes_existing_ai_tasks_and_forces_queue():
    queue = MagicMock()
    db = MagicMock()
    db.has_ai_tasks_for_record.return_value = True

    forced = enqueue_task_extraction(queue, db, 7, "Text", "ops", "Weekly")

    assert forced is True
    db.delete_ai_tasks_by_record.assert_called_once_with(7)
    queue.enqueue_task_extraction.assert_called_once_with(
        7,
        "Text",
        "ops",
        "Weekly",
        force=True,
        source="recording",
    )


def test_enqueue_task_extraction_without_existing_tasks_does_not_delete():
    queue = MagicMock()
    db = MagicMock()
    db.has_ai_tasks_for_record.return_value = False

    forced = enqueue_task_extraction(queue, db, 7, "Text", "ops", "Weekly")

    assert forced is False
    db.delete_ai_tasks_by_record.assert_not_called()
    queue.enqueue_task_extraction.assert_called_once()


def test_enqueue_post_transcription_summary_requires_text_and_queue():
    queue = MagicMock()
    assert enqueue_post_transcription_summary(queue, 7, "", "Weekly") is False
    assert enqueue_post_transcription_summary(None, 7, "Text", "Weekly") is False
    assert enqueue_post_transcription_summary(queue, 7, "Text", "Weekly") is True
    queue.enqueue_recording_summary.assert_called_once_with(7, "Text", "Weekly", source="recording")


def test_configure_legacy_ai_thread_wires_signals_and_starts():
    widget = FakeWidget()

    thread = configure_legacy_ai_thread(widget, FakeAssistantThread, "summary", "Text")

    assert thread.prefix == ""
    assert thread.task_type == "summary"
    assert thread.text == "Text"
    assert thread.started is True
    assert widget.statuses == ["Running summary..."]
    assert widget.progresses == [-1]

    thread.task_completed.emit("summary", "Done")
    thread.error.emit("bad")
    thread.finished.emit()
    assert widget.on_ai_finished.call_args.args == ("summary", "Done")
    assert widget.on_ai_error.call_args.args == ("bad",)
    assert widget._clear_ai_thread_ref.call_count == 2


def test_refresh_global_tasks_sidebar_calls_capable_widgets_only():
    capable = MagicMock()
    incapable = object()

    refresh_global_tasks_sidebar([capable, incapable])

    capable.refresh_tasks_sidebar.assert_called_once()
