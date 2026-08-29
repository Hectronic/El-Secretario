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

from unittest.mock import patch

from src.app.summary_queue.helpers import (
    parse_task_extraction_result,
    read_audio_duration_seconds,
)


def test_parse_task_extraction_result_accepts_plain_json_list():
    result = parse_task_extraction_result('["Task 1", " ", "Task 2", 3]')

    assert result == ["Task 1", "Task 2"]


def test_parse_task_extraction_result_accepts_wrapped_json_list():
    result = parse_task_extraction_result("Tasks:\n[\"Call client\", \"Send notes\"]\nDone.")

    assert result == ["Call client", "Send notes"]


def test_parse_task_extraction_result_rejects_non_list_payload():
    assert parse_task_extraction_result('{"task": "Call client"}') == []
    assert parse_task_extraction_result("not json") == []


@patch("src.app.summary_queue.helpers.logging.warning")
def test_read_audio_duration_seconds_returns_zero_when_probe_fails(mock_warning):
    duration = read_audio_duration_seconds("/tmp/does-not-exist.wav")

    assert duration == 0.0
    mock_warning.assert_called_once()
