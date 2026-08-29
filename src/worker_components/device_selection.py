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

import platform

import torch


def get_optimal_device(force_cpu: bool = False, model_size: str = "base") -> tuple[str, str]:
    """Select runtime device/compute profile for Whisper transcription.

    The policy intentionally favors safer profiles when VRAM is constrained and
    keeps historical Windows defaults for runtime stability.
    """
    is_windows = platform.system() == "Windows"

    if not force_cpu and torch.cuda.is_available():
        if is_windows:
            return ("cuda", "float16")

        try:
            gpu_mem_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            if model_size in ("large-v3", "large", "medium") and gpu_mem_gb <= 8:
                return ("cuda", "int8")
            if gpu_mem_gb > 8:
                return ("cuda", "float16")
        except Exception:
            pass
        return ("cuda", "int8")

    if is_windows:
        return ("cpu", "float32")
    return ("cpu", "int8")
