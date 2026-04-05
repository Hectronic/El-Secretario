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

import unittest
import sys
import types
import builtins
from unittest.mock import MagicMock, patch
from src.worker import (
    TranscriberThread,
    SearchThread,
    ChatThread,
    _ensure_sherpa_onnx_model_ready,
    get_transcription_preflight_error,
    _resolve_sherpa_onnx_model_config,
    _run_sherpa_onnx_transcription,
)
import os
import numpy as np
import tempfile

class TestTranscriberThread(unittest.TestCase):
    @patch('src.worker.WhisperModel')
    @patch('os.path.getsize')
    @patch('src.worker.platform.system', return_value="Linux")
    @patch('src.worker._get_pyannote_pipeline_class')
    def test_transcription(self, mock_get_pyannote, _mock_system, mock_getsize, MockWhisper):
        # Setup Mock
        mock_getsize.return_value = 1024
        mock_get_pyannote.return_value = None
        mock_model = MockWhisper.return_value
        Segment = MagicMock()
        Segment.start = 0.0
        Segment.end = 1.0
        Segment.text = "Hello world"
        
        mock_model.transcribe.return_value = ([Segment], None)
        
        thread = TranscriberThread("test.wav")
        
        # Mock signals
        thread.finished = MagicMock()
        thread.progress = MagicMock()
        thread.status_update = MagicMock()
        thread.error = MagicMock()
        
        thread.run()
        
        # Verify finished signal called with a dict containing the text
        args, _ = thread.finished.emit.call_args
        result = args[0]
        self.assertIsInstance(result, dict)
        self.assertEqual(result['text'], "Hello world")
        mock_get_pyannote.assert_not_called()

    @patch('src.worker.torch.cuda.is_available')
    @patch('src.worker.torch.cuda.get_device_properties')
    @patch('src.worker.platform.system', return_value="Linux")
    def test_get_optimal_device_with_cuda(self, _mock_system, mock_props, mock_cuda):
        from src.worker import get_optimal_device
        
        # Mock GPU with 6GB VRAM
        mock_cuda.return_value = True
        mock_props.return_value.total_memory = 6 * (1024**3)  # 6GB
        
        # Test with small model - should use int8 for safety on 6GB GPU
        device, compute_type = get_optimal_device(force_cpu=False, model_size="base")
        self.assertEqual(device, "cuda")
        self.assertEqual(compute_type, "int8")
        
        # Test with large model on 6GB GPU - should use int8
        device, compute_type = get_optimal_device(force_cpu=False, model_size="large-v3")
        self.assertEqual(device, "cuda")
        self.assertEqual(compute_type, "int8")
        
        # Test with force_cpu=True
        device, compute_type = get_optimal_device(force_cpu=True, model_size="base")
        self.assertEqual(device, "cpu")
        self.assertEqual(compute_type, "int8")
    
    @patch('src.worker.torch.cuda.is_available')
    @patch('src.worker.platform.system', return_value="Linux")
    def test_get_optimal_device_without_cuda(self, _mock_system, mock_cuda):
        from src.worker import get_optimal_device
        
        mock_cuda.return_value = False
        device, compute_type = get_optimal_device(force_cpu=False, model_size="base")
        self.assertEqual(device, "cpu")
        self.assertEqual(compute_type, "int8")

    @patch('src.worker.torch.cuda.is_available')
    @patch('src.worker.torch.cuda.get_device_properties')
    def test_get_optimal_device_with_large_gpu_prefers_float16(self, mock_props, mock_cuda):
        from src.worker import get_optimal_device

        mock_cuda.return_value = True
        mock_props.return_value.total_memory = 12 * (1024**3)
        device, compute_type = get_optimal_device(force_cpu=False, model_size="base")
        self.assertEqual(device, "cuda")
        self.assertEqual(compute_type, "float16")

    @patch('src.worker.torch.cuda.is_available')
    @patch('src.worker.torch.cuda.get_device_properties', side_effect=RuntimeError("gpu err"))
    @patch('src.worker.platform.system', return_value="Linux")
    def test_get_optimal_device_cuda_properties_error_defaults_int8(self, _mock_system, _mock_props, mock_cuda):
        from src.worker import get_optimal_device

        mock_cuda.return_value = True
        device, compute_type = get_optimal_device(force_cpu=False, model_size="base")
        self.assertEqual(device, "cuda")
        self.assertEqual(compute_type, "int8")

    @patch('src.worker.platform.system', return_value="Windows")
    @patch('src.worker.torch.cuda.is_available', return_value=True)
    def test_get_optimal_device_windows_cuda_prefers_float16(self, _mock_cuda, _mock_system):
        from src.worker import get_optimal_device

        device, compute_type = get_optimal_device(force_cpu=False, model_size="large-v3")
        self.assertEqual(device, "cuda")
        self.assertEqual(compute_type, "float16")

    @patch('src.worker.platform.system', return_value="Windows")
    @patch('src.worker.torch.cuda.is_available', return_value=False)
    def test_get_optimal_device_windows_cpu_prefers_float32(self, _mock_cuda, _mock_system):
        from src.worker import get_optimal_device

        device, compute_type = get_optimal_device(force_cpu=False, model_size="base")
        self.assertEqual(device, "cpu")
        self.assertEqual(compute_type, "float32")

    @patch('src.worker.platform.system', return_value="Windows")
    def test_windows_remaps_int8_compute_type_in_thread_init(self, _mock_system):
        # On Windows, we remap int8 to float16 on CUDA for stability.
        thread_cuda = TranscriberThread("test.wav", device="cuda", compute_type="int8")
        self.assertEqual(thread_cuda.compute_type, "float16")

        # On Windows CPU, we now prefer int8_float32 over pure float32/int8 to avoid native crashes.
        thread_cpu = TranscriberThread("test.wav", device="cpu", compute_type="int8")
        self.assertEqual(thread_cpu.compute_type, "int8_float32")

        thread_cpu_explicit = TranscriberThread("test.wav", device="cpu", compute_type="float32")
        self.assertEqual(thread_cpu_explicit.compute_type, "int8_float32")

    @patch("src.worker.platform.system", return_value="Windows")
    @patch("src.worker.os.path.getsize", return_value=100)
    @patch("src.worker._run_transcription_in_subprocess")
    @patch("src.worker.torch.cuda.is_available", return_value=False)
    def test_windows_subprocess_native_crash_retries_cpu_profiles(
        self, _mock_cuda_available, _mock_run_subprocess, _mock_getsize, _mock_system
    ):
        crash_error = RuntimeError(
            "Transcription subprocess crashed with exit code 3221225477 "
            "(possible native crash in faster-whisper/ctranslate2)."
        )
        _mock_run_subprocess.side_effect = [
            crash_error,
            [{"start": 0.0, "end": 1.0, "text": "Recovered"}],
        ]

        thread = TranscriberThread("test.wav", device="cpu", compute_type="int8_float32")
        thread.finished = MagicMock()
        thread.progress = MagicMock()
        thread.status_update = MagicMock()
        thread.error = MagicMock()

        thread.run()

        first_call = _mock_run_subprocess.call_args_list[0].kwargs
        second_call = _mock_run_subprocess.call_args_list[1].kwargs
        self.assertEqual(first_call["device"], "cpu")
        self.assertEqual(first_call["compute_type"], "int8_float32")
        self.assertEqual(second_call["device"], "cpu")
        self.assertEqual(second_call["compute_type"], "float32")
        self.assertEqual(thread.device, "cpu")
        self.assertEqual(thread.compute_type, "float32")
        thread.finished.emit.assert_called_once()
        thread.error.emit.assert_not_called()

    @patch("src.worker.platform.system", return_value="Windows")
    @patch("src.worker.os.path.getsize", return_value=100)
    @patch("src.worker._run_transcription_in_subprocess")
    @patch("src.worker.torch.cuda.is_available", return_value=False)
    def test_windows_subprocess_cuda_failure_falls_back_to_cpu(
        self, _mock_cuda_available, _mock_run_subprocess, _mock_getsize, _mock_system
    ):
        _mock_run_subprocess.side_effect = [
            RuntimeError("out of memory"),
            [{"start": 0.0, "end": 1.0, "text": "Recovered from CUDA failure"}],
        ]

        thread = TranscriberThread("test.wav", device="cuda", compute_type="float16")
        thread.finished = MagicMock()
        thread.progress = MagicMock()
        thread.status_update = MagicMock()
        thread.error = MagicMock()

        thread.run()

        first_call = _mock_run_subprocess.call_args_list[0].kwargs
        second_call = _mock_run_subprocess.call_args_list[1].kwargs
        self.assertEqual(first_call["device"], "cuda")
        self.assertEqual(second_call["device"], "cpu")
        self.assertEqual(second_call["compute_type"], "int8_float32")
        self.assertTrue(thread.force_cpu)
        thread.finished.emit.assert_called_once()
        thread.error.emit.assert_not_called()

    @patch("src.worker.platform.system", return_value="Windows")
    @patch("src.worker.os.path.getsize", return_value=100)
    @patch("src.worker._run_transcription_in_subprocess")
    @patch("src.worker.torch.cuda.is_available", return_value=False)
    def test_windows_native_crash_falls_back_to_smaller_model(
        self, _mock_cuda_available, _mock_run_subprocess, _mock_getsize, _mock_system
    ):
        native_crash = RuntimeError(
            "Transcription subprocess crashed with exit code 3221225477 "
            "(possible native crash in faster-whisper/ctranslate2)."
        )
        _mock_run_subprocess.side_effect = [
            native_crash,
            native_crash,
            native_crash,
            [{"start": 0.0, "end": 1.0, "text": "Recovered with medium"}],
        ]

        thread = TranscriberThread("test.wav", model_size="large-v3", device="cpu", compute_type="int8_float32")
        thread.finished = MagicMock()
        thread.progress = MagicMock()
        thread.status_update = MagicMock()
        thread.error = MagicMock()

        thread.run()

        calls = _mock_run_subprocess.call_args_list
        self.assertEqual(calls[0].kwargs["model_size"], "large-v3")
        self.assertEqual(calls[1].kwargs["model_size"], "large-v3")
        self.assertEqual(calls[2].kwargs["model_size"], "large-v3")
        self.assertEqual(calls[3].kwargs["model_size"], "medium")
        self.assertEqual(thread.model_size, "medium")
        thread.finished.emit.assert_called_once()
        thread.error.emit.assert_not_called()

    @patch("src.worker.platform.system", return_value="Windows")
    @patch("src.worker.os.path.getsize", return_value=100)
    @patch("src.worker._run_openai_whisper_fallback")
    @patch("src.worker._run_transcription_in_subprocess")
    @patch("src.worker.torch.cuda.is_available", return_value=False)
    def test_windows_native_crash_uses_openai_whisper_compat_fallback(
        self,
        _mock_cuda_available,
        _mock_run_subprocess,
        _mock_openai_fallback,
        _mock_getsize,
        _mock_system,
    ):
        native_crash = RuntimeError(
            "Transcription subprocess crashed with exit code 3221225477 "
            "(possible native crash in faster-whisper/ctranslate2)."
        )
        _mock_run_subprocess.side_effect = [native_crash] * 9
        _mock_openai_fallback.return_value = [
            {"start": 0.0, "end": 1.0, "text": "Recovered with openai-whisper"}
        ]

        thread = TranscriberThread("test.wav", model_size="large-v3", device="cpu", compute_type="int8_float32")
        thread.finished = MagicMock()
        thread.progress = MagicMock()
        thread.status_update = MagicMock()
        thread.error = MagicMock()

        thread.run()

        _mock_openai_fallback.assert_called_once()
        thread.finished.emit.assert_called_once()
        thread.error.emit.assert_not_called()

    def test_openai_whisper_fallback_prefers_local_audio_loading(self):
        from src.worker import _run_openai_whisper_fallback

        fake_model = MagicMock()
        fake_model.transcribe.return_value = {
            "segments": [{"start": 0.0, "end": 1.0, "text": "ok"}]
        }
        fake_whisper_module = types.SimpleNamespace(load_model=MagicMock(return_value=fake_model))
        prepared_audio = np.array([0.1, -0.2, 0.3], dtype=np.float32)

        with patch.dict(sys.modules, {"whisper": fake_whisper_module}), \
             patch("src.worker._prepare_audio_for_openai_whisper", return_value=prepared_audio):
            segments = _run_openai_whisper_fallback(
                audio_path="test.wav",
                model_size="large-v3",
                language=None,
            )

        fake_whisper_module.load_model.assert_called_once_with("large")
        transcribe_arg = fake_model.transcribe.call_args[0][0]
        self.assertIsInstance(transcribe_arg, np.ndarray)
        self.assertEqual(segments[0]["text"], "ok")

    def test_openai_whisper_fallback_uses_path_mode_when_local_load_fails(self):
        from src.worker import _run_openai_whisper_fallback

        fake_model = MagicMock()
        fake_model.transcribe.return_value = {
            "segments": [{"start": 0.0, "end": 1.0, "text": "ok"}]
        }
        fake_whisper_module = types.SimpleNamespace(load_model=MagicMock(return_value=fake_model))

        with patch.dict(sys.modules, {"whisper": fake_whisper_module}), \
             patch("src.worker._prepare_audio_for_openai_whisper", side_effect=RuntimeError("audio decode failed")):
            segments = _run_openai_whisper_fallback(
                audio_path="test.wav",
                model_size="base",
                language="es",
            )

        transcribe_arg = fake_model.transcribe.call_args[0][0]
        self.assertEqual(transcribe_arg, "test.wav")
        self.assertEqual(segments[0]["text"], "ok")

    def test_openai_whisper_fallback_raises_clear_error_when_ffmpeg_missing(self):
        from src.worker import _run_openai_whisper_fallback

        fake_model = MagicMock()
        fake_model.transcribe.side_effect = FileNotFoundError("[WinError 2] missing executable")
        fake_whisper_module = types.SimpleNamespace(load_model=MagicMock(return_value=fake_model))

        with patch.dict(sys.modules, {"whisper": fake_whisper_module}), \
             patch("src.worker._prepare_audio_for_openai_whisper", side_effect=RuntimeError("audio decode failed")):
            with self.assertRaises(RuntimeError) as ctx:
                _run_openai_whisper_fallback(
                    audio_path="test.wav",
                    model_size="base",
                    language=None,
                )

        self.assertIn("FFmpeg is not installed", str(ctx.exception))

    def test_resolve_sherpa_onnx_model_config_detects_transducer_layout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for filename in ("tokens.txt", "encoder.onnx", "decoder.onnx", "joiner.onnx"):
                with open(os.path.join(tmpdir, filename), "w", encoding="utf-8") as f:
                    f.write("x")

            config = _resolve_sherpa_onnx_model_config(tmpdir, "auto")

        self.assertEqual(config["type"], "transducer")
        self.assertTrue(config["encoder"].endswith("encoder.onnx"))

    def test_run_sherpa_onnx_transcription_requires_installed_package(self):
        settings = MagicMock()
        settings.value.side_effect = lambda key, default=None, type=None: {
            "sherpa_onnx_model_dir": "/tmp/missing",
            "sherpa_onnx_model_type": "auto",
        }.get(key, default)

        original_import = builtins.__import__

        def failing_import(name, *args, **kwargs):
            if name == "sherpa_onnx":
                raise ImportError("missing sherpa_onnx")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=failing_import):
            with self.assertRaises(RuntimeError) as ctx:
                _run_sherpa_onnx_transcription(
                    audio_path="test.wav",
                    language=None,
                    settings=settings,
                )

        self.assertIn("sherpa-onnx", str(ctx.exception))

    def test_run_sherpa_onnx_transcription_returns_single_segment(self):
        fake_recognizer = MagicMock()
        fake_stream = MagicMock()
        fake_stream.result = types.SimpleNamespace(text="hello from sherpa")
        fake_recognizer.create_stream.return_value = fake_stream
        fake_module = types.SimpleNamespace(
            OfflineRecognizer=types.SimpleNamespace(
                from_paraformer=MagicMock(return_value=fake_recognizer)
            )
        )
        fake_soundfile = types.SimpleNamespace(
            read=MagicMock(return_value=(np.array([0.1, -0.2, 0.3], dtype=np.float32), 16000))
        )
        settings = MagicMock()

        with tempfile.TemporaryDirectory() as tmpdir:
            for filename in ("tokens.txt", "model.onnx"):
                with open(os.path.join(tmpdir, filename), "w", encoding="utf-8") as f:
                    f.write("x")
            settings.value.side_effect = lambda key, default=None, type=None: {
                "sherpa_onnx_model_dir": tmpdir,
                "sherpa_onnx_model_type": "paraformer",
            }.get(key, default)
            with patch.dict(
                sys.modules,
                {
                    "sherpa_onnx": fake_module,
                    "soundfile": fake_soundfile,
                },
            ):
                segments = _run_sherpa_onnx_transcription(
                    audio_path="test.wav",
                    language="es",
                    settings=settings,
                )

        fake_recognizer.decode_streams.assert_called_once()
        self.assertEqual(segments, [{"start": 0.0, "end": 3 / 16000, "text": "hello from sherpa"}])

    def test_transcription_preflight_error_for_missing_sherpa_dir(self):
        settings = MagicMock()
        settings.value.side_effect = lambda key, default=None, type=None: {
            "sherpa_onnx_model_dir": "/tmp/does-not-exist-secretario",
            "sherpa_onnx_auto_download": False,
        }.get(key, default)

        error = get_transcription_preflight_error("sherpa-onnx", settings)

        self.assertIn("does not exist", error)
        self.assertIn("Settings -> Audio", error)

    def test_transcription_preflight_allows_missing_sherpa_dir_when_auto_download_enabled(self):
        settings = MagicMock()
        settings.value.side_effect = lambda key, default=None, type=None: {
            "sherpa_onnx_model_dir": "/tmp/does-not-exist-secretario",
            "sherpa_onnx_auto_download": True,
        }.get(key, default)

        error = get_transcription_preflight_error("sherpa-onnx", settings)

        self.assertIsNone(error)

    @patch("src.worker._download_sherpa_onnx_model")
    @patch("src.worker._resolve_existing_sherpa_model_dir")
    def test_ensure_sherpa_model_ready_auto_downloads_when_missing(
        self, mock_resolve_existing, mock_download
    ):
        settings = MagicMock()
        settings.value.side_effect = lambda key, default=None, type=None: {
            "sherpa_onnx_model_dir": "/tmp/sherpa-model",
            "sherpa_onnx_model_type": "auto",
            "sherpa_onnx_auto_download": True,
            "sherpa_onnx_model_url": "https://example.com/model.tar.bz2",
        }.get(key, default)
        expected_config = {"type": "whisper", "tokens": "/tmp/sherpa-model/tokens.txt"}
        mock_resolve_existing.side_effect = [
            (None, None),
            ("/tmp/sherpa-model/extracted", expected_config),
        ]

        model_dir, model_config = _ensure_sherpa_onnx_model_ready(settings)

        mock_download.assert_called_once()
        self.assertEqual(model_dir, "/tmp/sherpa-model/extracted")
        self.assertEqual(model_config, expected_config)
        settings.setValue.assert_any_call("sherpa_onnx_model_dir", "/tmp/sherpa-model/extracted")

    @patch("src.worker.QSettings")
    @patch("src.worker.os.path.getsize", return_value=100)
    @patch("src.worker._run_sherpa_onnx_transcription")
    def test_sherpa_onnx_model_uses_sherpa_backend_and_persists_settings(
        self, mock_sherpa_run, _mock_getsize, MockQSettings
    ):
        mock_sherpa_run.return_value = [{"start": 0.0, "end": 1.0, "text": "local sherpa ok"}]
        settings_instance = MagicMock()
        MockQSettings.return_value = settings_instance

        thread = TranscriberThread(
            "test.wav",
            model_size="sherpa-onnx",
            backend_preference="auto",
            total_duration=1.0,
        )
        thread.finished = MagicMock()
        thread.progress = MagicMock()
        thread.status_update = MagicMock()
        thread.error = MagicMock()

        thread.run()

        mock_sherpa_run.assert_called_once()
        self.assertEqual(thread.effective_backend, "sherpa-onnx")
        settings_instance.setValue.assert_any_call("transcription_backend", "sherpa-onnx")
        settings_instance.setValue.assert_any_call("whisper_model", "sherpa-onnx")
        thread.finished.emit.assert_called_once()
        thread.error.emit.assert_not_called()

    @patch("src.worker.QSettings")
    @patch("src.worker.os.path.getsize", return_value=100)
    @patch("src.worker._run_transcription_in_subprocess")
    @patch("src.worker._run_openai_whisper_fallback")
    def test_backend_preference_openai_persists_working_settings(
        self, _mock_openai_fallback, _mock_run_subprocess, _mock_getsize, MockQSettings
    ):
        _mock_openai_fallback.return_value = [
            {"start": 0.0, "end": 1.0, "text": "openai backend ok"}
        ]
        settings_instance = MagicMock()
        MockQSettings.return_value = settings_instance

        thread = TranscriberThread(
            "test.wav",
            model_size="base",
            device="cpu",
            compute_type="int8_float32",
            backend_preference="openai-whisper",
        )
        thread.finished = MagicMock()
        thread.progress = MagicMock()
        thread.status_update = MagicMock()
        thread.error = MagicMock()

        thread.run()

        _mock_run_subprocess.assert_not_called()
        self.assertEqual(thread.effective_backend, "openai-whisper")
        settings_instance.setValue.assert_any_call("transcription_backend", "openai-whisper")
        settings_instance.setValue.assert_any_call("whisper_model", thread.model_size)
        settings_instance.setValue.assert_any_call("rec_config/model", thread.model_size)
        thread.finished.emit.assert_called_once()


class TestSearchAndChatThreads(unittest.TestCase):
    def test_search_thread_success(self):
        rag = MagicMock()
        rag.search.return_value = [{"id": 1}]
        thread = SearchThread(rag, "hello")
        thread.finished = MagicMock()
        thread.error = MagicMock()

        thread.run()

        thread.finished.emit.assert_called_once_with([{"id": 1}])
        thread.error.emit.assert_not_called()

    def test_search_thread_error(self):
        rag = MagicMock()
        rag.search.side_effect = Exception("boom")
        thread = SearchThread(rag, "hello")
        thread.finished = MagicMock()
        thread.error = MagicMock()

        thread.run()

        thread.error.emit.assert_called_once_with("boom")
        thread.finished.emit.assert_not_called()

    def test_chat_thread_success(self):
        provider = MagicMock()
        provider.chat.return_value = "ok-response"

        with patch("src.ai_provider.get_ai_provider", return_value=provider), \
             patch("PyQt6.QtCore.QSettings"):
            thread = ChatThread("k", "q", "ctx", history=[{"role": "user", "content": "hi"}], model_name="x")
            thread.finished = MagicMock()
            thread.error = MagicMock()
            thread.run()

        thread.finished.emit.assert_called_once_with("ok-response")
        thread.error.emit.assert_not_called()

    def test_chat_thread_error(self):
        with patch("src.ai_provider.get_ai_provider", side_effect=Exception("provider fail")), \
             patch("PyQt6.QtCore.QSettings"):
            thread = ChatThread("k", "q", "ctx")
            thread.finished = MagicMock()
            thread.error = MagicMock()
            thread.run()

        thread.error.emit.assert_called_once_with("provider fail")
        thread.finished.emit.assert_not_called()

if __name__ == '__main__':
    unittest.main()
