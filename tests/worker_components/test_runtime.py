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

from src.worker_components.runtime import should_use_gpu_for_diarization


@patch("src.worker_components.runtime.torch.cuda.is_available", return_value=True)
@patch("src.worker_components.runtime.torch.cuda.device_count", return_value=1)
@patch("src.worker_components.runtime.torch.cuda.mem_get_info")
def test_should_use_gpu_for_diarization_rejects_low_free_vram(
    mock_mem_info, _mock_count, _mock_available
):
    mock_mem_info.return_value = (int(2 * 1024**3), int(8 * 1024**3))
    use_gpu, reason = should_use_gpu_for_diarization(force_cpu=False, min_free_vram_gb=3.0)
    assert use_gpu is False
    assert "free vram too low" in reason.lower()


@patch("src.worker_components.runtime.torch.cuda.is_available", return_value=True)
@patch("src.worker_components.runtime.torch.cuda.device_count", return_value=1)
@patch("src.worker_components.runtime.torch.cuda.mem_get_info")
def test_should_use_gpu_for_diarization_accepts_sufficient_free_vram(
    mock_mem_info, _mock_count, _mock_available
):
    mock_mem_info.return_value = (int(4 * 1024**3), int(8 * 1024**3))
    use_gpu, reason = should_use_gpu_for_diarization(
        force_cpu=False,
        min_free_vram_gb=3.0,
        min_free_ratio=0.35,
    )
    assert use_gpu is True
    assert "sufficient" in reason.lower()


def test_should_use_gpu_for_diarization_honors_force_cpu():
    use_gpu, reason = should_use_gpu_for_diarization(force_cpu=True, min_free_vram_gb=3.0)
    assert use_gpu is False
    assert "force_cpu" in reason.lower()


@patch("src.worker_components.runtime.torch.cuda.is_available", return_value=True)
@patch("src.worker_components.runtime.torch.cuda.device_count", return_value=1)
@patch("src.worker_components.runtime.torch.cuda.mem_get_info")
def test_should_use_gpu_for_diarization_rejects_low_free_ratio(
    mock_mem_info, _mock_count, _mock_available
):
    # Enough absolute free memory, but too little proportion free.
    mock_mem_info.return_value = (int(3.2 * 1024**3), int(16 * 1024**3))
    use_gpu, reason = should_use_gpu_for_diarization(
        force_cpu=False,
        min_free_vram_gb=3.0,
        min_free_ratio=0.35,
    )
    assert use_gpu is False
    assert "ratio too low" in reason.lower()
