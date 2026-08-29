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

import os

from src.stt_providers.sherpa_onnx import (
    default_sherpa_model_dir,
    default_sherpa_model_url,
    find_existing_file,
    get_transcription_preflight_error,
    resolve_sherpa_onnx_model_config,
)


def test_default_model_paths_are_stable():
    model_dir = default_sherpa_model_dir()
    assert os.path.basename(model_dir) == "sherpa-onnx"
    assert os.path.basename(os.path.dirname(model_dir)) == "models"
    assert default_sherpa_model_url().endswith("sherpa-onnx-whisper-tiny.tar.bz2")


def test_find_existing_file_returns_first_match(tmp_path):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    file_one = model_dir / "tokens.txt"
    file_one.write_text("a")
    file_two = model_dir / "other-tokens.txt"
    file_two.write_text("b")

    assert find_existing_file(str(model_dir), ["*tokens.txt"]) in {str(file_one), str(file_two)}


def test_resolve_sherpa_onnx_model_config_detects_transducer_layout(tmp_path):
    model_dir = tmp_path / "sherpa"
    model_dir.mkdir()
    (model_dir / "tokens.txt").write_text("tok")
    (model_dir / "encoder.onnx").write_text("x")
    (model_dir / "decoder.onnx").write_text("x")
    (model_dir / "joiner.onnx").write_text("x")

    config = resolve_sherpa_onnx_model_config(str(model_dir), "auto")
    assert config["type"] == "transducer"
    assert config["tokens"].endswith("tokens.txt")


def test_get_transcription_preflight_error_returns_none_for_non_sherpa_backend():
    class DummySettings:
        def value(self, *_args, **_kwargs):
            return None

    assert get_transcription_preflight_error("base", DummySettings()) is None
