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


def test_persist_working_transcription_settings_keeps_user_preferences_untouched():
    qsettings = MagicMock()

    worker_settings.persist_working_transcription_settings(
        qsettings,
        effective_backend="openai-whisper",
        model_size="base",
        device="cpu",
        force_cpu=False,
        compute_type="float32",
    )

    written_keys = {call.args[0] for call in qsettings.setValue.call_args_list}
    assert "transcription_backend" not in written_keys
    assert "whisper_model" not in written_keys
    assert "rec_config/model" not in written_keys
    assert "force_cpu" not in written_keys
    assert "compute_type" not in written_keys


def test_persist_working_transcription_settings_records_last_runtime_snapshot():
    qsettings = MagicMock()

    worker_settings.persist_working_transcription_settings(
        qsettings,
        effective_backend="faster-whisper",
        model_size="base",
        device="cuda",
        force_cpu=False,
        compute_type="int8",
    )

    qsettings.setValue.assert_any_call("last_transcription_backend", "faster-whisper")
    qsettings.setValue.assert_any_call("last_transcription_model", "base")
    qsettings.setValue.assert_any_call("last_transcription_device", "cuda")
    qsettings.setValue.assert_any_call("last_transcription_force_cpu", False)
    qsettings.setValue.assert_any_call("last_transcription_compute_type", "int8")


def test_persist_working_transcription_settings_does_not_turn_cpu_fallback_into_preference():
    qsettings = MagicMock()

    worker_settings.persist_working_transcription_settings(
        qsettings,
        effective_backend="faster-whisper",
        model_size="base",
        device="cpu",
        force_cpu=False,
        compute_type="int8_float32",
    )

    written_keys = {call.args[0] for call in qsettings.setValue.call_args_list}
    assert "force_cpu" not in written_keys
    qsettings.setValue.assert_any_call("last_transcription_device", "cpu")
    qsettings.setValue.assert_any_call("last_transcription_force_cpu", False)


def test_get_subprocess_attempt_timeout_seconds_defaults_and_falls_back():
    qsettings = MagicMock()
    qsettings.value.return_value = "90"

    assert worker_settings.get_subprocess_attempt_timeout_seconds(qsettings) == 90

    qsettings.value.side_effect = RuntimeError("boom")
    assert worker_settings.get_subprocess_attempt_timeout_seconds(qsettings) in (120, 600)


def test_get_subprocess_attempt_timeout_for_duration_uses_baseline_for_short_audio():
    qsettings = MagicMock()
    qsettings.value.return_value = "120"

    timeout = worker_settings.get_subprocess_attempt_timeout_for_duration_seconds(
        qsettings,
        total_duration_seconds=30,
    )

    assert timeout == 336


def test_get_subprocess_attempt_timeout_for_duration_scales_for_long_audio_with_cap():
    qsettings = MagicMock()
    qsettings.value.return_value = "120"

    timeout = worker_settings.get_subprocess_attempt_timeout_for_duration_seconds(
        qsettings,
        total_duration_seconds=7200,  # 2 hours
    )

    assert timeout == 5400


def test_get_transcription_chunking_config_applies_defaults_and_clamps():
    qsettings = MagicMock()

    def _value(key, default=None, type=None):
        values = {
            "transcription_chunking_enabled": True,
            "transcription_chunk_threshold_seconds": 60,   # clamped to 300
            "transcription_chunk_size_seconds": 120,       # clamped to 180
            "transcription_chunk_overlap_seconds": 240,    # adjusted below chunk size
        }
        return values.get(key, default)

    qsettings.value.side_effect = _value
    cfg = worker_settings.get_transcription_chunking_config(qsettings)

    assert cfg["enabled"] is True
    assert cfg["threshold_seconds"] == 300
    assert cfg["chunk_size_seconds"] == 180
    assert cfg["overlap_seconds"] == 18
