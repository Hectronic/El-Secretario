"""Non-blocking, user initiated diarization access check."""
import threading
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, QTimer, pyqtSignal
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from src.worker_components.diarization_diagnostics import check_diarization
from src.ui.diarization_text import diarization_text


class _Signals(QObject):
    completed = pyqtSignal(int, object)


class _Check(QRunnable):
    def __init__(self, generation, token):
        super().__init__()
        self.generation = generation
        self.token = token
        self.signals = _Signals()
        self.cancelled = threading.Event()

    def run(self):
        result = check_diarization(self.token, cancelled=self.cancelled)
        self.token = ""
        self.signals.completed.emit(self.generation, result)


class DiarizationCheckWidget(QWidget):
    def __init__(self, field, token_input, parent=None):
        super().__init__(parent)
        self.token_input = token_input
        self._generation = 0
        self._checks = {}
        checks = self._checks
        self.destroyed.connect(lambda: [check.cancelled.set() for check in list(checks.values())])
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.timeout.connect(self._timed_out)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(field)
        self.check_button = QPushButton(diarization_text("Check diarization"))
        self.check_button.setAccessibleName(diarization_text("Check diarization availability"))
        layout.addWidget(self.check_button)
        self.cancel_button = QPushButton(diarization_text("Cancel check"))
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_check)
        layout.addWidget(self.cancel_button)
        self.status_label = QLabel(diarization_text("Diarization not checked."))
        self.status_label.setWordWrap(True)
        self.status_label.setAccessibleName(diarization_text("Diarization check result"))
        layout.addWidget(self.status_label)
        self.check_button.clicked.connect(self.start_check)
        self.token_input.textChanged.connect(self.invalidate)

    def invalidate(self):
        for check in self._checks.values():
            check.cancelled.set()
        self.cancel_button.setEnabled(False)
        self._generation += 1
        self._timeout.stop()
        self.status_label.setText(diarization_text("Diarization not checked for this token."))
        self.check_button.setEnabled(True)

    def start_check(self):
        self._generation += 1
        generation = self._generation
        self.check_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status_label.setText(diarization_text("Checking diarization…"))
        self._timeout.start(45000)
        check = _Check(generation, self.token_input.text().strip())
        self._checks[generation] = check
        check.signals.completed.connect(self._completed)
        QThreadPool.globalInstance().start(check)

    def cancel_check(self):
        for check in self._checks.values():
            check.cancelled.set()
        self._generation += 1
        self._timeout.stop()
        self.cancel_button.setEnabled(False)
        self.check_button.setEnabled(True)
        self.status_label.setText(diarization_text("Check cancelled. The current network request will finish in the background."))

    def _timed_out(self):
        for check in self._checks.values():
            check.cancelled.set()
        self.cancel_button.setEnabled(False)
        self._generation += 1
        self.check_button.setEnabled(True)
        self.status_label.setText(diarization_text("Check timed out. Retry when the network is available."))

    def _completed(self, generation, result):
        self._checks.pop(generation, None)
        if generation != self._generation:
            return
        self._timeout.stop()
        self.cancel_button.setEnabled(False)
        self.check_button.setEnabled(True)
        self.status_label.setText(f"{diarization_text(result.state)} ({result.checked_at}): "
                                  f"{diarization_text(result.message)} "
                                  f"{diarization_text('Save settings to use any token changes for transcription.')}")
