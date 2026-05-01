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

from src.stt_providers.sherpa_onnx.model_manager import (
    default_sherpa_model_dir,
    default_sherpa_model_url,
    download_sherpa_onnx_model,
    ensure_sherpa_onnx_model_ready,
    find_existing_file,
    get_transcription_preflight_error,
    iter_sherpa_candidate_dirs,
    resolve_existing_sherpa_model_dir,
    resolve_sherpa_onnx_model_config,
    safe_extract_tarball,
)
