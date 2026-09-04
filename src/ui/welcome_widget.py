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

import platform

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSettings, QTime, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen
from src.ui.welcome.button_factory import (
    create_big_button,
    create_round_button,
    create_squircle_button,
)
from src.ui.welcome.mic_runtime import WelcomeMicRuntime
from src.ui.welcome.capture_runtime import WelcomeCaptureRuntime
from src.ui.welcome.landing_actions import WelcomeLandingActions
from src.ui.welcome.layout import (
    apply_layout_density,
    build_welcome_layout,
    set_rec_button_size,
)
Recorder = None

class AnalogClockWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(92, 92)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(1000)

    def paintEvent(self, _event):
        side = min(self.width(), self.height())
        now = QTime.currentTime()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(side / 100.0, side / 100.0)

        painter.setPen(QPen(QColor("#CFD8DC"), 3))
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(-46, -46, 92, 92)

        for i in range(12):
            painter.save()
            painter.rotate(i * 30)
            painter.setPen(QPen(QColor("#78909C"), 2 if i % 3 else 3))
            painter.drawLine(0, -38, 0, -44)
            painter.restore()

        hour_angle = 30 * ((now.hour() % 12) + now.minute() / 60.0)
        minute_angle = 6 * (now.minute() + now.second() / 60.0)
        second_angle = 6 * now.second()

        painter.save()
        painter.rotate(hour_angle)
        painter.setPen(QPen(QColor("#37474F"), 5, cap=Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(0, 5), QPointF(0, -21))
        painter.restore()

        painter.save()
        painter.rotate(minute_angle)
        painter.setPen(QPen(QColor("#455A64"), 3, cap=Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(0, 7), QPointF(0, -30))
        painter.restore()

        painter.save()
        painter.rotate(second_angle)
        painter.setPen(QPen(QColor("#E53935"), 1.5, cap=Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(0, 9), QPointF(0, -33))
        painter.restore()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#E53935"))
        painter.drawEllipse(-3, -3, 6, 6)


class WelcomeWidget(QWidget):
    # Modified signal to include recording configuration
    new_recording_requested = pyqtSignal(dict)  # Emits config dict
    search_requested = pyqtSignal() # Kept for compatibility if needed, but likely unused now
    search_triggered = pyqtSignal(str)
    result_clicked = pyqtSignal(int)
    new_chat_requested = pyqtSignal()
    ask_chat_with_context_requested = pyqtSignal()
    new_note_requested = pyqtSignal()
    batch_process_requested = pyqtSignal()  # Kept for compatibility
    import_audio_requested = pyqtSignal(dict)  # Also include config for import
    notebooks_requested = pyqtSignal()
    maintenance_requested = pyqtSignal()  # Kept for compatibility
    tools_requested = pyqtSignal()  # Unified tools signal
    settings_requested = pyqtSignal() # New settings signal
    generate_daily_summary_requested = pyqtSignal()
    status_message_requested = pyqtSignal(str)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._is_windows = platform.system() == "Windows"
        self._compact_mode_active = False
        self.favorites_page = 0
        self.test_stream = None
        self.test_timer = QTimer()
        self.test_timer.timeout.connect(self.update_test_vu)
        self.settings = QSettings("Hectronic", "Secretario")
        self.current_amplitude = 0.0
        self.mic_runtime = WelcomeMicRuntime(self)
        self.capture_runtime = WelcomeCaptureRuntime(self)
        self.landing_actions = WelcomeLandingActions(self)
        self.init_ui()
        self.load_favorites()
        self.load_today()
        self._load_saved_config()
        self._connect_config_signals()

    def _load_saved_config(self):
        self.capture_runtime.load_saved_config()
        
    def _connect_config_signals(self):
        self.capture_runtime.connect_config_signals()

    def _save_config(self):
        self.capture_runtime.save_config()

    def _update_digital_clock(self):
        self.digital_clock_label.setText(QTime.currentTime().toString("HH:mm:ss"))
        self._sync_header_balance()

    def _sync_header_balance(self):
        if not hasattr(self, "header_left_spacer"):
            return
        clock_width = max(self.analog_clock.width(), self.digital_clock_label.sizeHint().width())
        self.header_left_spacer.setFixedWidth(clock_width)

    def init_ui(self):
        build_welcome_layout(self, AnalogClockWidget)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_layout_density()

    def _apply_layout_density(self, viewport_height=None):
        apply_layout_density(self, viewport_height)

    def _set_rec_button_size(self, size):
        set_rec_button_size(self, size)

    def populate_mics(self, keep_current=False):
        """Populate the microphone combo box with available devices."""
        global Recorder
        if Recorder is None:
            from src.audio import Recorder as _Recorder
            Recorder = _Recorder
        self.mic_runtime.populate_mics(recorder_getter=lambda: Recorder, keep_current=keep_current)

    def on_rescan_mics_clicked(self):
        self.mic_runtime.rescan(recorder_getter=lambda: Recorder)

    def toggle_mic_test(self):
        """Toggle microphone testing on/off."""
        import sounddevice as sd
        self.mic_runtime.toggle(sd_module=sd)

    def start_mic_test(self):
        """Start testing the selected microphone."""
        import sounddevice as sd
        self.mic_runtime.start(sd_module=sd)

    def stop_mic_test(self):
        """Stop testing the microphone."""
        self.mic_runtime.stop()

    def test_audio_callback(self, indata, frames, time, status):
        """Callback for test audio stream."""
        self.mic_runtime.audio_callback(indata, frames, time, status)

    def update_test_vu(self):
        """Update the test VU meter."""
        self.mic_runtime.update_vu()

    def get_recording_config(self):
        """Get the current recording configuration."""
        return self.capture_runtime.get_recording_config()

    def on_new_recording(self):
        """Emit new recording signal with configuration."""
        self.capture_runtime.request_capture(self.new_recording_requested)

    def on_import_audio(self):
        """Emit import audio signal with configuration."""
        self.capture_runtime.request_capture(self.import_audio_requested)

    def create_big_button(self, text, color, callback, width=200, height=150, class_name=None):
        return create_big_button(text, color, callback, width=width, height=height, class_name=class_name)

    def create_round_button(self, text, color, callback, size=120, class_name=None):
        return create_round_button(text, color, callback, size=size, class_name=class_name)

    def create_squircle_button(self, text, color, callback, width=100, height=90, class_name=None):
        return create_squircle_button(text, color, callback, width=width, height=height, class_name=class_name)

    def on_search_triggered(self):
        self.landing_actions.trigger_search()

    def display_results(self, results):
        self.landing_actions.display_results(results)

    def on_result_clicked(self, item):
        self.landing_actions.open_item(item)
        
    def load_favorites(self):
        self.landing_actions.load_favorites()

    def prev_page(self):
        self.landing_actions.previous_page()

    def next_page(self):
        self.landing_actions.next_page()
        
    def on_fav_clicked(self, item):
        self.landing_actions.open_item(item)

    def load_today(self):
        self.landing_actions.load_today()

    def on_today_clicked(self, item):
        self.landing_actions.open_item(item)

    def save_settings(self):
        """Save current settings to QSettings."""
        self.settings.setValue("whisper_model", self.model_combo.currentText())
        self.settings.setValue("whisper_language", self.lang_combo.currentText())
        self.settings.sync() # Ensure settings are written to disk

# End of assumed class content
