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

from typing import Any, Dict

from src.app.summary_queue.helpers import read_audio_duration_seconds


def build_transcription_worker_kwargs(settings, task: Dict) -> Dict[str, Any]:
    hf_token = settings.value("hf_token", "")
    force_cpu = settings.value("force_cpu", False, type=bool)
    compute_type = settings.value("compute_type", "auto")
    transcription_backend = settings.value("transcription_backend", "auto")
    if compute_type == "auto":
        compute_type = None

    return {
        "audio_path": task["audio_path"],
        "model_size": task["model_size"],
        "compute_type": compute_type,
        "language": task["language"],
        "hf_token": hf_token,
        "enable_diarization": task["diarization"],
        "total_duration": read_audio_duration_seconds(task["audio_path"]),
        "force_cpu": force_cpu,
        "backend_preference": transcription_backend,
    }

