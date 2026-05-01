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

from unittest.mock import MagicMock

from src.worker_components import settings as worker_settings


def test_persist_working_transcription_settings_uses_same_logic_for_all_backends():
    qsettings = MagicMock()

    worker_settings.persist_working_transcription_settings(
        qsettings,
        effective_backend="openai-whisper",
        model_size="base",
        device="cpu",
        force_cpu=False,
        compute_type="float32",
    )

    qsettings.setValue.assert_any_call("transcription_backend", "openai-whisper")
    qsettings.setValue.assert_any_call("whisper_model", "base")
    qsettings.setValue.assert_any_call("rec_config/model", "base")
    qsettings.setValue.assert_any_call("force_cpu", True)
    assert not any(call.args[0] == "compute_type" for call in qsettings.setValue.call_args_list)


def test_persist_working_transcription_settings_keeps_compute_type_for_faster_whisper():
    qsettings = MagicMock()

    worker_settings.persist_working_transcription_settings(
        qsettings,
        effective_backend="faster-whisper",
        model_size="base",
        device="cuda",
        force_cpu=False,
        compute_type="int8",
    )

    qsettings.setValue.assert_any_call("compute_type", "int8")


def test_get_subprocess_attempt_timeout_seconds_defaults_and_falls_back():
    qsettings = MagicMock()
    qsettings.value.return_value = "90"

    assert worker_settings.get_subprocess_attempt_timeout_seconds(qsettings) == 90

    qsettings.value.side_effect = RuntimeError("boom")
    assert worker_settings.get_subprocess_attempt_timeout_seconds(qsettings) in (120, 1800)
