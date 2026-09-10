"""Single-worker transcription runtime for recorded notebook entries."""

from dataclasses import dataclass

from PyQt6.QtCore import QSettings

from src.stt_providers.sherpa_onnx.model_manager import get_transcription_preflight_error
from src.transcription_options import get_saved_transcription_model
from src.worker_components.transcriber_thread import TranscriberThread


@dataclass(frozen=True)
class NotebookTranscriptionStartResult:
    started: bool
    preflight_error: str | None = None


class NotebookTranscriptionRuntime:
    def __init__(
        self,
        thread_factory=None,
        settings_factory=None,
        model_resolver=None,
        preflight_checker=None,
    ):
        self._thread_factory = thread_factory or TranscriberThread
        self._settings_factory = settings_factory or QSettings
        self._model_resolver = model_resolver or get_saved_transcription_model
        self._preflight_checker = preflight_checker or get_transcription_preflight_error
        self.thread = None

    def start(self, file_path, on_finished, on_error):
        if self.thread and self.thread.isRunning():
            return NotebookTranscriptionStartResult(started=False)
        settings = self._settings_factory("Hectronic", "Secretario")
        model_size = self._model_resolver(settings)
        preflight_error = self._preflight_checker(model_size, settings)
        if preflight_error:
            return NotebookTranscriptionStartResult(False, preflight_error)
        compute_type = settings.value("compute_type", "auto")
        self.thread = self._thread_factory(
            file_path,
            model_size=model_size,
            compute_type=None if compute_type == "auto" else compute_type,
            force_cpu=settings.value("force_cpu", False, type=bool),
            backend_preference=settings.value("transcription_backend", "auto"),
        )
        self.thread.finished.connect(on_finished)
        self.thread.error.connect(on_error)
        self.thread.finished.connect(self._clear_thread)
        self.thread.error.connect(self._clear_thread)
        self.thread.start()
        return NotebookTranscriptionStartResult(started=True)

    def _clear_thread(self, *_args):
        thread = self.thread
        self.thread = None
        if thread:
            thread.deleteLater()

    def cleanup(self):
        thread = self.thread
        if not thread:
            return
        if thread.isRunning():
            try:
                thread.requestInterruption()
                thread.quit()
                thread.wait(3000)
            except Exception:
                pass
        try:
            thread.deleteLater()
        except Exception:
            pass
        self.thread = None
