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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from src.app.summary_queue.history import QueueHistory


def test_queue_history_returns_newest_entries_first_and_copies_tasks():
    history = QueueHistory()
    task = {"type": "summary", "record_id": 1}

    history.append("queued", task)
    task["record_id"] = 2
    history.append("started", task, "Running")

    entries = history.newest_first()
    assert [entry["event"] for entry in entries] == ["started", "queued"]
    assert entries[0]["message"] == "Running"
    assert entries[1]["task"]["record_id"] == 1


def test_queue_history_limits_entries():
    history = QueueHistory(max_entries=2)

    history.append("one", {})
    history.append("two", {})
    history.append("three", {})

    assert len(history) == 2
    assert [entry["event"] for entry in history.newest_first()] == ["three", "two"]


def test_status_trace_deduplicates_consecutive_messages():
    history = QueueHistory()
    task = {"type": "transcription"}

    assert history.append_status_trace_once(task, "Retrying 1") is True
    assert history.append_status_trace_once(task, "Retrying 1") is False
    assert history.append_status_trace_once(task, "Retrying 2") is True

    messages = [entry["message"] for entry in history.newest_first()]
    assert messages == ["Retrying 2", "Retrying 1"]


def test_status_trace_can_be_reset_between_workers():
    history = QueueHistory()
    task = {"type": "transcription"}

    assert history.append_status_trace_once(task, "Retrying 1") is True
    assert history.append_status_trace_once(task, "Retrying 1") is False
    history.clear_status_dedup()
    assert history.append_status_trace_once(task, "Retrying 1") is True

