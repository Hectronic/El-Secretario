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

from unittest.mock import MagicMock, patch

from src.stt_providers.dispatcher import subprocess_transcribe_entry


def test_subprocess_transcribe_entry_routes_to_backend_handler():
    result_queue = MagicMock()

    with patch("src.stt_providers.dispatcher.BACKEND_HANDLERS", {"openai-whisper": lambda payload: [{"text": "ok"}]}):
        subprocess_transcribe_entry({"backend": "openai-whisper"}, result_queue)

    result_queue.put.assert_called_once_with({"ok": True, "segments": [{"text": "ok"}]})


def test_subprocess_transcribe_entry_reports_unsupported_backend():
    result_queue = MagicMock()

    subprocess_transcribe_entry({"backend": "missing-backend"}, result_queue)

    result_queue.put.assert_called_once()
    payload = result_queue.put.call_args.args[0]
    assert payload["ok"] is False
    assert "Unsupported transcription backend" in payload["error"]
