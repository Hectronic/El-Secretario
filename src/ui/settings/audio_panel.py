# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.

"""Audio and transcription settings panel."""

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.transcription_options import (
    DEFAULT_TRANSCRIPTION_MODEL,
    format_transcription_model_tooltip,
    get_sherpa_model_type_options,
    get_transcription_model_options,
    normalize_sherpa_model_type,
    normalize_transcription_model,
)
from src.worker_components.sherpa import default_sherpa_model_url


class AudioSettingsPanel(QWidget):
    """Panel for audio capture, transcription, and related runtime settings."""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        rec_label = QLabel("🎤 Recording Settings")
        rec_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #607D8B; margin-top: 10px;")
        form_layout.addRow(rec_label)

        lbl_mic = QLabel("Default Microphone:")
        lbl_mic.setStyleSheet("font-weight: bold;")
        mic_row = QHBoxLayout()
        mic_row.setContentsMargins(0, 0, 0, 0)
        mic_row.setSpacing(8)

        self.mic_combo = QComboBox()
        self._populate_mics()
        mic_row.addWidget(self.mic_combo, 1)

        self.rescan_mics_btn = QPushButton("🔄 Re-scan")
        self.rescan_mics_btn.setToolTip("Re-scan USB and system recording devices")
        self.rescan_mics_btn.clicked.connect(self._on_rescan_mics_clicked)
        mic_row.addWidget(self.rescan_mics_btn)

        saved_mic_index = self.settings.value("default_mic_index", None)
        saved_mic_name = self.settings.value("default_mic_name", "")
        prefer_index = self.settings.value("audio_prefer_device_index", False, type=bool)
        if prefer_index and saved_mic_index is not None:
            try:
                mic_index = int(saved_mic_index)
                index = self.mic_combo.findData(mic_index)
                if index >= 0:
                    self.mic_combo.setCurrentIndex(index)
            except (TypeError, ValueError):
                pass
        if self.mic_combo.currentIndex() <= 0 and saved_mic_name:
            index = self.mic_combo.findText(saved_mic_name)
            if index >= 0:
                self.mic_combo.setCurrentIndex(index)

        mic_row_widget = QWidget()
        mic_row_widget.setLayout(mic_row)
        form_layout.addRow(lbl_mic, mic_row_widget)

        self.mic_status_label = QLabel("")
        self.mic_status_label.setStyleSheet("color: gray; font-size: 12px;")
        form_layout.addRow("", self.mic_status_label)

        lbl_sys_audio = QLabel("System Audio Capture:")
        lbl_sys_audio.setStyleSheet("font-weight: bold;")
        self.sys_audio_check = QCheckBox("Capture audio from the machine (Speaker output)")
        self.sys_audio_check.setToolTip("Attempts to automatically find and record from the system monitor device.")
        self.sys_audio_check.setChecked(self.settings.value("capture_system_audio", False, type=bool))
        form_layout.addRow(lbl_sys_audio, self.sys_audio_check)

        trans_label = QLabel("📝 Transcription Engine")
        trans_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #607D8B; margin-top: 20px;")
        form_layout.addRow(trans_label)

        lbl_whisper = QLabel("Default Transcription Model:")
        lbl_whisper.setStyleSheet("font-weight: bold;")
        self.whisper_combo = QComboBox()
        self.whisper_combo.addItems(get_transcription_model_options())
        self.whisper_combo.setCurrentText(
            normalize_transcription_model(
                self.settings.value("whisper_model", DEFAULT_TRANSCRIPTION_MODEL)
            )
        )
        self.whisper_combo.setToolTip(format_transcription_model_tooltip(get_transcription_model_options()))
        form_layout.addRow(lbl_whisper, self.whisper_combo)

        lbl_sherpa_dir = QLabel("Sherpa-ONNX Model Dir:")
        lbl_sherpa_dir.setStyleSheet("font-weight: bold;")
        self.sherpa_model_dir_input = QLineEdit()
        self.sherpa_model_dir_input.setPlaceholderText("models/sherpa-onnx")
        self.sherpa_model_dir_input.setText(
            self.settings.value("sherpa_onnx_model_dir", "models/sherpa-onnx")
        )
        self.sherpa_model_dir_input.setToolTip(
            "Directory containing the local sherpa-onnx model files (tokens.txt and ONNX weights)."
        )
        form_layout.addRow(lbl_sherpa_dir, self.sherpa_model_dir_input)

        lbl_sherpa_type = QLabel("Sherpa-ONNX Model Type:")
        lbl_sherpa_type.setStyleSheet("font-weight: bold;")
        self.sherpa_model_type_combo = QComboBox()
        self.sherpa_model_type_combo.addItems(get_sherpa_model_type_options())
        self.sherpa_model_type_combo.setCurrentText(
            normalize_sherpa_model_type(self.settings.value("sherpa_onnx_model_type", "auto"))
        )
        form_layout.addRow(lbl_sherpa_type, self.sherpa_model_type_combo)

        lbl_sherpa_download = QLabel("Sherpa Auto-download:")
        lbl_sherpa_download.setStyleSheet("font-weight: bold;")
        self.sherpa_auto_download_check = QCheckBox("Download default sherpa-onnx model automatically if missing")
        self.sherpa_auto_download_check.setChecked(
            self.settings.value("sherpa_onnx_auto_download", True, type=bool)
        )
        form_layout.addRow(lbl_sherpa_download, self.sherpa_auto_download_check)

        lbl_sherpa_url = QLabel("Sherpa Model URL:")
        lbl_sherpa_url.setStyleSheet("font-weight: bold;")
        self.sherpa_model_url_input = QLineEdit()
        self.sherpa_model_url_input.setText(
            self.settings.value("sherpa_onnx_model_url", default_sherpa_model_url())
        )
        self.sherpa_model_url_input.setToolTip(
            "Official archive URL used when automatic download is enabled and the local model is missing."
        )
        form_layout.addRow(lbl_sherpa_url, self.sherpa_model_url_input)

        lbl_force_cpu = QLabel("Force CPU:")
        lbl_force_cpu.setStyleSheet("font-weight: bold;")
        self.force_cpu_check = QCheckBox("Disable GPU acceleration")
        self.force_cpu_check.setToolTip("Force transcription and diarization to use CPU even if GPU is available")
        self.force_cpu_check.setChecked(self.settings.value("force_cpu", False, type=bool))
        form_layout.addRow(lbl_force_cpu, self.force_cpu_check)

        lbl_compute = QLabel("Compute Type:")
        lbl_compute.setStyleSheet("font-weight: bold;")
        self.compute_combo = QComboBox()
        self.compute_combo.addItems(["auto", "int8", "int8_float16", "float16", "float32"])
        self.compute_combo.setCurrentText(self.settings.value("compute_type", "auto"))
        self.compute_combo.setToolTip(
            "int8: Best for GPUs with limited VRAM (6-8GB), fastest\n"
            "int8_float16: Hybrid precision, good balance\n"
            "float16: Better quality, needs more VRAM\n"
            "float32: Highest quality, needs most VRAM\n"
            "auto: Let the app decide based on your GPU"
        )
        form_layout.addRow(lbl_compute, self.compute_combo)

        lbl_backend = QLabel("Transcription Backend:")
        lbl_backend.setStyleSheet("font-weight: bold;")
        self.backend_combo = QComboBox()
        self.backend_combo.addItems(["auto", "faster-whisper", "openai-whisper"])
        self.backend_combo.setCurrentText(self.settings.value("transcription_backend", "auto"))
        self.backend_combo.setToolTip(
            "auto: Try faster-whisper and fallback if needed\n"
            "faster-whisper: Prefer ctranslate2 backend\n"
            "openai-whisper: Torch backend, slower but stable on some Windows setups"
        )
        form_layout.addRow(lbl_backend, self.backend_combo)

        lbl_rag_index = QLabel("Auto-index to RAG:")
        lbl_rag_index.setStyleSheet("font-weight: bold;")
        self.rag_auto_index_check = QCheckBox("Index new/updated notes and transcriptions in RAG")
        self.rag_auto_index_check.setChecked(self.settings.value("auto_index_rag", True, type=bool))
        self.rag_auto_index_check.setToolTip(
            "When enabled, newly saved content is indexed for semantic search/chat."
        )
        form_layout.addRow(lbl_rag_index, self.rag_auto_index_check)

        advanced_label = QLabel("🛠 Advanced Device Detection")
        advanced_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #607D8B; margin-top: 20px;")
        form_layout.addRow(advanced_label)

        lbl_rescan_before_capture = QLabel("Pre-capture Re-scan:")
        lbl_rescan_before_capture.setStyleSheet("font-weight: bold;")
        self.rescan_before_capture_check = QCheckBox("Re-scan audio inputs before recording/import")
        self.rescan_before_capture_check.setToolTip(
            "Recommended on Windows when USB microphones are not detected consistently."
        )
        self.rescan_before_capture_check.setChecked(
            self.settings.value("audio_rescan_before_capture", True, type=bool)
        )
        form_layout.addRow(lbl_rescan_before_capture, self.rescan_before_capture_check)

        lbl_prefer_index = QLabel("Device Match Strategy:")
        lbl_prefer_index.setStyleSheet("font-weight: bold;")
        self.prefer_index_check = QCheckBox("Prefer saved microphone index over name")
        self.prefer_index_check.setToolTip(
            "Useful when USB device names change or duplicate names exist."
        )
        self.prefer_index_check.setChecked(
            self.settings.value("audio_prefer_device_index", False, type=bool)
        )
        form_layout.addRow(lbl_prefer_index, self.prefer_index_check)

        layout.addLayout(form_layout)

        info_label = QLabel(
            "These settings affect how audio is captured and processed by the transcription engine."
        )
        info_label.setStyleSheet("color: gray; font-size: 13px; margin-top: 10px;")
        layout.addWidget(info_label)

        layout.addStretch()

    def _populate_mics(self):
        """Populate microphone list."""
        import os

        previous_data = self.mic_combo.currentData() if hasattr(self, "mic_combo") else None
        previous_text = self.mic_combo.currentText() if hasattr(self, "mic_combo") else ""
        self.mic_combo.clear()
        self.mic_combo.addItem("System Default", None)
        if os.environ.get("EL_SECRETARIO_SKIP_AUDIO_ENUM", "").strip().lower() in {"1", "true", "yes"}:
            self._restore_mic_selection(previous_data, previous_text)
            return
        try:
            from src.audio import Recorder

            devices = Recorder.get_input_devices()
            for idx, name in devices:
                self.mic_combo.addItem(name, idx)
        except Exception:
            pass
        self._restore_mic_selection(previous_data, previous_text)

    def _restore_mic_selection(self, preferred_data, preferred_text):
        if preferred_data is not None:
            by_data_idx = self.mic_combo.findData(preferred_data)
            if by_data_idx >= 0:
                self.mic_combo.setCurrentIndex(by_data_idx)
                return
        if preferred_text:
            by_text_idx = self.mic_combo.findText(preferred_text)
            if by_text_idx >= 0:
                self.mic_combo.setCurrentIndex(by_text_idx)

    def _on_rescan_mics_clicked(self):
        before = self.mic_combo.count()
        self._populate_mics()
        after = self.mic_combo.count()
        if after > 1:
            self.mic_status_label.setText(f"Detected {after - 1} input device(s).")
            self.mic_status_label.setStyleSheet("color: #4CAF50; font-size: 12px;")
        else:
            self.mic_status_label.setText("No input devices found (using System Default).")
            self.mic_status_label.setStyleSheet("color: #FF9800; font-size: 12px;")
        if before != after:
            QTimer.singleShot(4000, lambda: self.mic_status_label.setText(""))

    def save(self):
        """Save audio settings."""
        self.settings.setValue("default_mic_name", self.mic_combo.currentText() if self.mic_combo.currentData() is not None else "")
        self.settings.setValue("default_mic_index", self.mic_combo.currentData())
        self.settings.setValue("capture_system_audio", self.sys_audio_check.isChecked())
        self.settings.setValue("whisper_model", self.whisper_combo.currentText())
        self.settings.setValue(
            "sherpa_onnx_model_dir",
            self.sherpa_model_dir_input.text().strip() or "models/sherpa-onnx",
        )
        self.settings.setValue(
            "sherpa_onnx_model_type",
            self.sherpa_model_type_combo.currentText(),
        )
        self.settings.setValue(
            "sherpa_onnx_auto_download",
            self.sherpa_auto_download_check.isChecked(),
        )
        self.settings.setValue(
            "sherpa_onnx_model_url",
            self.sherpa_model_url_input.text().strip() or default_sherpa_model_url(),
        )
        self.settings.setValue("force_cpu", self.force_cpu_check.isChecked())
        self.settings.setValue("compute_type", self.compute_combo.currentText())
        self.settings.setValue("transcription_backend", self.backend_combo.currentText())
        self.settings.setValue("auto_index_rag", self.rag_auto_index_check.isChecked())
        self.settings.setValue("audio_rescan_before_capture", self.rescan_before_capture_check.isChecked())
        self.settings.setValue("audio_prefer_device_index", self.prefer_index_check.isChecked())
