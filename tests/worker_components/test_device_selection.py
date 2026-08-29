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

from types import SimpleNamespace
from unittest.mock import patch

from src.worker_components.device_selection import get_optimal_device


@patch("src.worker_components.device_selection.platform.system", return_value="Linux")
@patch("src.worker_components.device_selection.torch.cuda.is_available", return_value=True)
@patch("src.worker_components.device_selection.torch.cuda.get_device_properties")
def test_get_optimal_device_linux_small_gpu_prefers_int8(mock_props, _mock_cuda, _mock_system):
    mock_props.return_value = SimpleNamespace(total_memory=6 * 1024**3)
    assert get_optimal_device(force_cpu=False, model_size="large-v3") == ("cuda", "int8")


@patch("src.worker_components.device_selection.platform.system", return_value="Linux")
@patch("src.worker_components.device_selection.torch.cuda.is_available", return_value=True)
@patch("src.worker_components.device_selection.torch.cuda.get_device_properties")
def test_get_optimal_device_linux_big_gpu_prefers_float16(mock_props, _mock_cuda, _mock_system):
    mock_props.return_value = SimpleNamespace(total_memory=12 * 1024**3)
    assert get_optimal_device(force_cpu=False, model_size="base") == ("cuda", "float16")


@patch("src.worker_components.device_selection.platform.system", return_value="Linux")
@patch("src.worker_components.device_selection.torch.cuda.is_available", return_value=True)
@patch(
    "src.worker_components.device_selection.torch.cuda.get_device_properties",
    side_effect=RuntimeError("gpu err"),
)
def test_get_optimal_device_linux_gpu_props_error_falls_back_to_int8(_mock_props, _mock_cuda, _mock_system):
    assert get_optimal_device(force_cpu=False, model_size="base") == ("cuda", "int8")


@patch("src.worker_components.device_selection.platform.system", return_value="Windows")
@patch("src.worker_components.device_selection.torch.cuda.is_available", return_value=True)
def test_get_optimal_device_windows_cuda_prefers_float16(_mock_cuda, _mock_system):
    assert get_optimal_device(force_cpu=False, model_size="large-v3") == ("cuda", "float16")


@patch("src.worker_components.device_selection.platform.system", return_value="Windows")
@patch("src.worker_components.device_selection.torch.cuda.is_available", return_value=False)
def test_get_optimal_device_windows_cpu_prefers_float32(_mock_cuda, _mock_system):
    assert get_optimal_device(force_cpu=False, model_size="base") == ("cpu", "float32")


@patch("src.worker_components.device_selection.platform.system", return_value="Linux")
@patch("src.worker_components.device_selection.torch.cuda.is_available", return_value=True)
def test_get_optimal_device_force_cpu_overrides_cuda(_mock_cuda, _mock_system):
    assert get_optimal_device(force_cpu=True, model_size="base") == ("cpu", "int8")
