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

from src.worker_components.runtime import diarization_batch_sizes, should_use_gpu_for_diarization


def test_diarization_batch_sizes_scale_with_free_gpu_memory_and_leave_cpu_conservative():
    assert diarization_batch_sizes(use_gpu=False, free_vram_gb=12) == (1, 1)
    assert diarization_batch_sizes(use_gpu=True, free_vram_gb=None) == (1, 1)
    assert diarization_batch_sizes(use_gpu=True, free_vram_gb=2.4) == (1, 1)
    assert diarization_batch_sizes(use_gpu=True, free_vram_gb=3.0) == (2, 2)
    assert diarization_batch_sizes(use_gpu=True, free_vram_gb=6.0) == (4, 4)
    assert diarization_batch_sizes(use_gpu=True, free_vram_gb=10.0) == (8, 8)


@patch("src.worker_components.runtime.torch.cuda.is_available", return_value=True)
@patch("src.worker_components.runtime.torch.cuda.device_count", return_value=1)
@patch("src.worker_components.runtime.torch.cuda.mem_get_info")
def test_should_use_gpu_for_diarization_attempts_cuda_with_low_free_vram(
    mock_mem_info, _mock_count, _mock_available
):
    mock_mem_info.return_value = (int(2 * 1024**3), int(8 * 1024**3))
    use_gpu, reason = should_use_gpu_for_diarization(force_cpu=False)
    assert use_gpu is True
    assert "attempting diarization on gpu" in reason.lower()


@patch("src.worker_components.runtime.torch.cuda.is_available", return_value=True)
@patch("src.worker_components.runtime.torch.cuda.device_count", return_value=1)
@patch("src.worker_components.runtime.torch.cuda.mem_get_info")
def test_should_use_gpu_for_diarization_accepts_sufficient_free_vram(
    mock_mem_info, _mock_count, _mock_available
):
    mock_mem_info.return_value = (int(4 * 1024**3), int(8 * 1024**3))
    use_gpu, reason = should_use_gpu_for_diarization(force_cpu=False)
    assert use_gpu is True
    assert "attempting diarization on gpu" in reason.lower()


def test_should_use_gpu_for_diarization_honors_force_cpu():
    use_gpu, reason = should_use_gpu_for_diarization(force_cpu=True)
    assert use_gpu is False
    assert "force_cpu" in reason.lower()


@patch("src.worker_components.runtime.torch.cuda.is_available", return_value=True)
@patch("src.worker_components.runtime.torch.cuda.device_count", return_value=1)
@patch("src.worker_components.runtime.torch.cuda.mem_get_info")
def test_should_use_gpu_for_diarization_does_not_force_cpu_for_low_free_ratio(
    mock_mem_info, _mock_count, _mock_available
):
    # Enough absolute free memory, but too little proportion free.
    mock_mem_info.return_value = (int(3.2 * 1024**3), int(16 * 1024**3))
    use_gpu, reason = should_use_gpu_for_diarization(
        force_cpu=False,
    )
    assert use_gpu is True
    assert "attempting diarization on gpu" in reason.lower()
