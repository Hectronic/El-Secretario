from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

from src.notebook_database import NotebookDBManager
from src.ui.notebook_widget import NotebookWidget
from src.ui.notebooks.transcription_runtime import NotebookTranscriptionRuntime


class _Recorder(QObject):
    amplitude_changed = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.is_recording = False

    def stop(self):
        self.is_recording = False
        return None


class _Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, value):
        for callback in list(self.callbacks):
            callback(value)


class _ImmediateTranscriber:
    def __init__(self, *_args, **_kwargs):
        self.finished = _Signal()
        self.error = _Signal()
        self.running = False

    def isRunning(self):
        return self.running

    def start(self):
        self.running = True
        self.finished.emit({"text": "Persisted voice note"})
        self.running = False

    def requestInterruption(self):
        self.running = False

    def quit(self):
        pass

    def wait(self, _timeout):
        return True

    def deleteLater(self):
        pass


class _Settings:
    def value(self, _key, default=None, **_kwargs):
        return default


def test_notebook_widget_transcribes_refreshes_and_deletes_audio_entry(qtbot, tmp_path, monkeypatch):
    db = NotebookDBManager(str(tmp_path / "notebooks.sqlite"))
    notebook_id = db.create_notebook("Research")
    audio_path = tmp_path / "voice-note.wav"
    audio_path.write_bytes(b"voice")
    entry_id = db.add_audio_entry(notebook_id, str(audio_path), 2.0)
    runtime = NotebookTranscriptionRuntime(
        thread_factory=_ImmediateTranscriber,
        settings_factory=lambda *_args: _Settings(),
        model_resolver=lambda _settings: "base",
        preflight_checker=lambda *_args: None,
    )
    widget = NotebookWidget(db, notebook_id, "Research", _Recorder(), transcription_runtime=runtime)
    qtbot.addWidget(widget)
    changes = []
    widget.entries_changed.connect(lambda: changes.append(widget.entries_list.count()))

    widget.start_transcription(entry_id, str(audio_path))

    entry = db.get_entries(notebook_id)[0]
    assert entry["content"] == "Persisted voice note"
    assert widget.entries_list.count() == 1
    assert changes == [1]
    monkeypatch.setattr(
        "src.ui.notebook_widget.QMessageBox.question",
        lambda *_args: QMessageBox.StandardButton.Yes,
    )
    widget.delete_entry(entry)

    assert db.get_entries(notebook_id) == []
    assert not audio_path.exists()
