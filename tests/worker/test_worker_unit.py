import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.worker_components import device_selection, engine as worker_engine, runtime as worker_runtime, subprocess_runner
from src.worker_components.threads import ChatThread, SearchThread
from src.worker_components.transcriber_thread import TranscriberThread
from src.stt_providers.sherpa_onnx import model_manager as sherpa_model_manager


class TestWorkerUnit(unittest.TestCase):
    @patch("src.worker_components.subprocess_runner.run_backend_subprocess")
    def test_run_backend_subprocess_delegates(self, mock_run):
        mock_run.return_value = [{"text": "ok"}]
        result = subprocess_runner.run_backend_subprocess(backend="faster-whisper", payload={"audio_path": "x.wav"}, timeout_seconds=11)
        self.assertEqual(result[0]["text"], "ok")
        mock_run.assert_called_once_with(backend="faster-whisper", payload={"audio_path": "x.wav"}, timeout_seconds=11)

    @patch("src.worker_components.subprocess_runner.run_transcription_in_subprocess")
    def test_run_transcription_in_subprocess_delegates(self, mock_run):
        mock_run.return_value = [{"text": "ok"}]
        result = subprocess_runner.run_transcription_in_subprocess(
            audio_path="x.wav",
            model_size="base",
            device="cpu",
            compute_type="int8",
            language="es",
            timeout_seconds=77,
        )
        self.assertEqual(result[0]["text"], "ok")
        mock_run.assert_called_once()

    @patch("src.worker_components.subprocess_runner.run_openai_whisper_fallback")
    def test_run_openai_fallback_delegates(self, mock_run):
        mock_run.return_value = [{"text": "ok"}]
        result = subprocess_runner.run_openai_whisper_fallback(audio_path="x.wav", model_size="base", language="es")
        self.assertEqual(result[0]["text"], "ok")
        mock_run.assert_called_once_with(audio_path="x.wav", model_size="base", language="es")

    @patch("src.worker_components.subprocess_runner.run_sherpa_onnx_transcription")
    @patch("src.stt_providers.sherpa_onnx.model_manager.ensure_sherpa_onnx_model_ready")
    def test_run_sherpa_onnx_transcription_delegates(self, mock_ensure, mock_run):
        mock_ensure.return_value = ("/m", {"type": "transducer"})
        mock_run.return_value = [{"text": "ok"}]
        settings = MagicMock()
        model_dir, model_config = sherpa_model_manager.ensure_sherpa_onnx_model_ready(settings)
        result = subprocess_runner.run_sherpa_onnx_transcription(audio_path="x.wav", language="es", model_dir=model_dir, model_config=model_config)
        self.assertEqual(result[0]["text"], "ok")
        mock_ensure.assert_called_once_with(settings)
        mock_run.assert_called_once_with(
            audio_path="x.wav",
            language="es",
            model_dir="/m",
            model_config={"type": "transducer"},
        )

    @patch("src.stt_providers.sherpa_onnx.model_manager.safe_extract_tarball")
    def test_safe_extract_tarball_delegates(self, mock_safe_extract):
        sherpa_model_manager.safe_extract_tarball("archive.tar.bz2", "/tmp/dest")
        mock_safe_extract.assert_called_once_with("archive.tar.bz2", "/tmp/dest")

    @patch("src.stt_providers.sherpa_onnx.model_manager.download_sherpa_onnx_model")
    def test_download_sherpa_model_delegates(self, mock_download):
        cb = MagicMock()
        sherpa_model_manager.download_sherpa_onnx_model("https://example.com/model.tar.bz2", "/tmp", status_callback=cb)
        mock_download.assert_called_once_with("https://example.com/model.tar.bz2", "/tmp", status_callback=cb)

    @patch("src.stt_providers.sherpa_onnx.model_manager.ensure_sherpa_onnx_model_ready")
    def test_ensure_sherpa_model_ready_delegates(self, mock_ensure):
        settings = MagicMock()
        mock_ensure.return_value = ("/m", {"type": "transducer"})
        model_dir, config = sherpa_model_manager.ensure_sherpa_onnx_model_ready(settings)
        self.assertEqual(model_dir, "/m")
        self.assertEqual(config["type"], "transducer")
        mock_ensure.assert_called_once_with(settings)

    @patch("src.stt_providers.sherpa_onnx.model_manager.get_transcription_preflight_error")
    def test_preflight_delegates(self, mock_preflight):
        settings = MagicMock()
        mock_preflight.return_value = "bad"
        self.assertEqual(sherpa_model_manager.get_transcription_preflight_error("sherpa-onnx", settings), "bad")
        mock_preflight.assert_called_once_with("sherpa-onnx", settings)

    @patch("src.worker_components.runtime.pkg_version", return_value="<not-installed>")
    def test_pkg_version_not_installed(self, _mock_pkg_version):
        self.assertEqual(worker_runtime.pkg_version("not-installed-pkg"), "<not-installed>")

    @patch("src.worker_components.runtime.pkg_version", return_value="<unknown>")
    def test_pkg_version_unknown_error(self, _mock_pkg_version):
        self.assertEqual(worker_runtime.pkg_version("broken-pkg"), "<unknown>")

    def test_get_pyannote_pipeline_class_caches_none_after_import_error(self):
        worker_runtime._PYANNOTE_IMPORT_ATTEMPTED = False
        worker_runtime._PYANNOTE_PIPELINE_CLS = None
        with patch("builtins.__import__", side_effect=ImportError("missing")):
            result = worker_runtime.get_pyannote_pipeline_class()
        self.assertIsNone(result)
        self.assertTrue(worker_runtime._PYANNOTE_IMPORT_ATTEMPTED)

    @patch("src.worker_components.transcriber_thread.platform.system", return_value="Linux")
    @patch("src.worker_components.transcriber_thread.QSettings")
    def test_get_subprocess_attempt_timeout_defaults_on_settings_error(self, MockQSettings, _mock_system):
        MockQSettings.side_effect = RuntimeError("settings-fail")
        thread = TranscriberThread("test.wav")
        self.assertEqual(thread._get_subprocess_attempt_timeout_seconds(), 600)

    @patch("src.worker_components.transcriber_thread.platform.system", return_value="Linux")
    @patch("src.worker_components.transcriber_thread.QSettings")
    def test_get_subprocess_attempt_timeout_scales_with_duration(self, MockQSettings, _mock_system):
        qsettings = MagicMock()
        qsettings.value.return_value = "600"
        MockQSettings.return_value = qsettings
        thread = TranscriberThread("test.wav", total_duration=3600)  # 1 hour
        self.assertEqual(thread._get_subprocess_attempt_timeout_seconds(), 4620)

    def test_is_transcription_fatal_failure_matches_timeout_and_crash(self):
        self.assertTrue(worker_engine.is_transcription_fatal_failure("Transcription subprocess timed out."))
        self.assertTrue(
            worker_engine.is_transcription_fatal_failure(
                "Transcription subprocess crashed with exit code -9 (possible native crash in transcription backend)."
            )
        )
        self.assertFalse(worker_engine.is_transcription_fatal_failure("boom"))

    @patch("src.worker_components.transcriber_thread.trim_audio_segment")
    @patch("src.worker_components.transcriber_thread.tempfile.TemporaryDirectory")
    def test_chunked_transcription_splits_audio_and_offsets_segments(self, mock_tmp_dir, mock_trim):
        tmp_ctx = MagicMock()
        tmp_ctx.__enter__.return_value = "/tmp/chunks"
        tmp_ctx.__exit__.return_value = None
        mock_tmp_dir.return_value = tmp_ctx

        thread = TranscriberThread("long.wav", model_size="base", total_duration=2500)
        calls = []

        def _fake_once(*, audio_path, duration_seconds):
            calls.append((audio_path, duration_seconds))
            return [{"start": 0.0, "end": 10.0, "text": "ok"}]

        thread._transcribe_faster_whisper_once = _fake_once
        thread.isInterruptionRequested = MagicMock(return_value=False)
        thread.status_update = MagicMock()

        merged = thread._transcribe_faster_whisper_chunked(
            chunk_cfg={
                "enabled": True,
                "threshold_seconds": 1800,
                "chunk_size_seconds": 1000,
                "overlap_seconds": 100,
            }
        )

        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[0][1], 1000)
        self.assertEqual(calls[1][1], 1000)
        self.assertEqual(calls[2][1], 700)
        self.assertEqual(len(merged), 3)
        self.assertEqual(merged[0]["start"], 0.0)
        self.assertEqual(merged[1]["start"], 900.0)
        self.assertEqual(merged[2]["start"], 1800.0)
        self.assertEqual(mock_trim.call_count, 3)

    @patch("src.worker_components.transcriber_thread._run_transcription_in_subprocess")
    @patch("src.worker_components.transcriber_thread.QSettings")
    @patch("src.worker_components.transcriber_thread.platform.system", return_value="Linux")
    def test_run_chunking_cancellation_exits_without_finished_or_error(
        self,
        _mock_system,
        MockQSettings,
        _mock_run_subprocess,
    ):
        qsettings = MagicMock()
        qsettings.value.side_effect = lambda key, default=None, type=None: {
            "transcription_chunking_enabled": True,
            "transcription_chunk_threshold_seconds": 10,
            "transcription_chunk_size_seconds": 10,
            "transcription_chunk_overlap_seconds": 1,
            "transcription_attempt_timeout_seconds": 600,
        }.get(key, default)
        MockQSettings.return_value = qsettings

        thread = TranscriberThread("long.wav", model_size="base", total_duration=120)
        thread.finished = MagicMock()
        thread.progress = MagicMock()
        thread.status_update = MagicMock()
        thread.error = MagicMock()
        thread._transcribe_faster_whisper_chunked = MagicMock(return_value=[])
        thread.isInterruptionRequested = MagicMock(return_value=True)

        thread.run()

        thread.status_update.emit.assert_any_call("Cancelled.")
        thread.finished.emit.assert_not_called()
        thread.error.emit.assert_not_called()


class TestTranscriberThreadRunBranches(unittest.TestCase):
    def _build_thread(self, **kwargs):
        thread = TranscriberThread("test.wav", **kwargs)
        thread.finished = MagicMock()
        thread.progress = MagicMock()
        thread.status_update = MagicMock()
        thread.error = MagicMock()
        return thread

    @patch("src.worker_components.transcriber_thread.platform.system", return_value="Linux")
    @patch("src.worker_components.transcriber_thread.QSettings")
    @patch("src.worker_components.transcriber_thread.os.path.getsize", return_value=100)
    @patch("src.worker_components.transcriber_thread._run_transcription_in_subprocess", side_effect=RuntimeError("boom"))
    def test_run_non_windows_runtimeerror_emits_error(
        self, _mock_run, _mock_getsize, MockQSettings, _mock_system
    ):
        MockQSettings.return_value = MagicMock()
        thread = self._build_thread(model_size="base", device="cpu", compute_type="int8")
        thread.run()
        thread.error.emit.assert_called_once()
        self.assertEqual(
            thread.error.emit.call_args.args[0],
            "No se pudo completar la transcripción. Vuelve a intentarlo. "
            "Si el problema continúa, consulta el registro de la aplicación.",
        )

    @patch("src.worker_components.transcriber_thread.platform.system", return_value="Windows")
    @patch("src.worker_components.transcriber_thread.torch.cuda.empty_cache")
    @patch("src.worker_components.transcriber_thread.torch.cuda.synchronize", side_effect=RuntimeError("sync-fail"))
    @patch("src.worker_components.transcriber_thread.torch.cuda.is_available", return_value=True)
    @patch("src.worker_components.transcriber_thread.QSettings")
    @patch("src.worker_components.transcriber_thread.os.path.getsize", return_value=100)
    @patch("src.worker_components.transcriber_thread._run_openai_whisper_fallback", side_effect=RuntimeError("fallback exploded"))
    @patch("src.worker_components.transcriber_thread._run_transcription_in_subprocess")
    def test_run_windows_fallback_failure_emits_error_and_tolerates_cuda_sync_error(
        self,
        _mock_run,
        _mock_openai_fallback,
        _mock_getsize,
        MockQSettings,
        _mock_cuda_available,
        _mock_cuda_sync,
        mock_cuda_empty_cache,
        _mock_system,
    ):
        native_crash = RuntimeError(
            "Transcription subprocess crashed with exit code 3221225477 "
            "(possible native crash in faster-whisper/ctranslate2)."
        )
        _mock_run.side_effect = [native_crash] * 9
        MockQSettings.return_value = MagicMock()

        thread = self._build_thread(model_size="large-v3", device="cpu", compute_type="int8_float32")
        thread.run()

        thread.error.emit.assert_called_once()
        self.assertEqual(
            thread.error.emit.call_args.args[0],
            "No se pudo completar la transcripción. Vuelve a intentarlo. "
            "Si el problema continúa, consulta el registro de la aplicación.",
        )
        mock_cuda_empty_cache.assert_called_once()

    @patch("src.worker_components.transcriber_thread.platform.system", return_value="Linux")
    @patch("src.worker_components.transcriber_thread.QSettings")
    @patch("src.worker_components.transcriber_thread.os.path.getsize", return_value=100)
    @patch("src.worker_components.transcriber_thread._run_transcription_in_subprocess")
    def test_run_cancelled_during_progress_loop(self, mock_run_subprocess, _mock_getsize, MockQSettings, _mock_system):
        mock_run_subprocess.return_value = [{"start": 1.0, "end": 2.0, "text": "hello"}]
        MockQSettings.return_value = MagicMock()
        thread = self._build_thread(model_size="base", device="cpu", compute_type="int8", total_duration=10)
        thread.isInterruptionRequested = MagicMock(return_value=True)

        thread.run()

        thread.status_update.emit.assert_any_call("Cancelled.")
        thread.finished.emit.assert_not_called()
        thread.error.emit.assert_not_called()

    @patch("src.worker_components.transcriber_thread.platform.system", return_value="Linux")
    @patch("src.worker_components.transcriber_thread._should_use_gpu_for_diarization", return_value=(False, "test guard"))
    @patch("src.worker_components.transcriber_thread.QSettings")
    @patch("src.worker_components.transcriber_thread.os.path.getsize", return_value=100)
    @patch("src.worker_components.transcriber_thread._get_pyannote_pipeline_class")
    @patch("src.worker_components.transcriber_thread._run_transcription_in_subprocess")
    def test_run_diarization_labels_and_scaled_progress(
        self,
        mock_run_subprocess,
        mock_get_pipeline_cls,
        _mock_getsize,
        MockQSettings,
        _mock_should_use_gpu,
        _mock_system,
    ):
        mock_run_subprocess.return_value = [
            {"start": 0.0, "end": 5.0, "text": "uno"},
            {"start": 5.0, "end": 10.0, "text": "dos"},
        ]
        MockQSettings.return_value = MagicMock()

        diarization = MagicMock()
        diarization.itertracks.return_value = [
            (SimpleNamespace(start=0.0, end=5.0), None, "SPEAKER_01"),
            (SimpleNamespace(start=5.0, end=10.0), None, "SPEAKER_02"),
        ]
        pipeline = MagicMock()
        pipeline.return_value = diarization
        pipeline_cls = MagicMock()
        pipeline_cls.from_pretrained.return_value = pipeline
        mock_get_pipeline_cls.return_value = pipeline_cls

        thread = self._build_thread(
            model_size="base",
            device="cpu",
            compute_type="int8",
            total_duration=10,
            enable_diarization=True,
            hf_token="hf_x",
        )
        thread.isInterruptionRequested = MagicMock(return_value=False)
        thread.run()

        emitted_progress = [c.args[0] for c in thread.progress.emit.call_args_list if c.args]
        self.assertIn(40, emitted_progress)
        self.assertIn(80, emitted_progress)
        self.assertIn(90, emitted_progress)
        self.assertIn(100, emitted_progress)
        result = thread.finished.emit.call_args.args[0]
        self.assertIn("[SPEAKER_01]", result["text"])
        self.assertIn("[SPEAKER_02]", result["text"])
        pipeline.to.assert_not_called()

    @patch("src.worker_components.transcriber_thread.platform.system", return_value="Linux")
    @patch("src.worker_components.transcriber_thread.QSettings")
    @patch("src.worker_components.transcriber_thread.os.path.getsize", return_value=100)
    @patch("src.worker_components.transcriber_thread.logging.warning")
    @patch("src.worker_components.transcriber_thread._get_pyannote_pipeline_class", return_value=None)
    @patch("src.worker_components.transcriber_thread._run_transcription_in_subprocess")
    def test_run_diarization_requested_but_pyannote_unavailable_logs_warning(
        self,
        mock_run_subprocess,
        _mock_get_pipeline_cls,
        mock_log_warning,
        _mock_getsize,
        MockQSettings,
        _mock_system,
    ):
        mock_run_subprocess.return_value = [{"start": 0.0, "end": 1.0, "text": "ok"}]
        MockQSettings.return_value = MagicMock()

        thread = self._build_thread(
            model_size="base",
            device="cpu",
            compute_type="int8",
            enable_diarization=True,
            hf_token="hf_x",
            total_duration=5,
        )
        thread.isInterruptionRequested = MagicMock(return_value=False)
        thread.run()

        mock_log_warning.assert_any_call("Diarization requested but pyannote.audio is unavailable.")
        thread.finished.emit.assert_called_once()



if __name__ == "__main__":
    unittest.main()
