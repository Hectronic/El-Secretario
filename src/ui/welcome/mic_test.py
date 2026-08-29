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

import numpy as np


STOP_BUTTON_STYLE = """
    QPushButton {
        background-color: #f44336;
        color: white;
        border-radius: 5px;
        padding: 5px;
    }
    QPushButton:hover {
        background-color: #d32f2f;
    }
"""


TEST_BUTTON_STYLE = """
    QPushButton {
        background-color: #2196F3;
        color: white;
        border-radius: 5px;
        padding: 5px;
    }
    QPushButton:hover {
        background-color: #1976D2;
    }
"""


VU_STYLE_HIGH = """
    QProgressBar { border: 2px solid #555; border-radius: 5px; background-color: #333; }
    QProgressBar::chunk { background-color: #f44336; }
"""

VU_STYLE_MEDIUM = """
    QProgressBar { border: 2px solid #555; border-radius: 5px; background-color: #333; }
    QProgressBar::chunk { background-color: #4CAF50; }
"""

VU_STYLE_LOW = """
    QProgressBar { border: 2px solid #555; border-radius: 5px; background-color: #333; }
    QProgressBar::chunk { background-color: #2196F3; }
"""


def calculate_rms(indata) -> float:
    return float(np.sqrt(np.mean(indata**2)))


def vu_value(amplitude: float) -> int:
    return min(100, int(amplitude * 1000))


def vu_style_for_value(value: int) -> str:
    if value > 70:
        return VU_STYLE_HIGH
    if value > 30:
        return VU_STYLE_MEDIUM
    return VU_STYLE_LOW


def start_mic_test(
    *,
    sd_module,
    device_index,
    audio_callback,
    vu_meter,
    status_label,
    test_button,
    test_timer,
    sample_rates=(16000, 44100, 48000, 22050),
):
    for rate in sample_rates:
        try:
            stream = sd_module.InputStream(
                samplerate=rate,
                channels=1,
                callback=audio_callback,
                device=device_index,
            )
            stream.start()
            vu_meter.show()
            status_label.setText(f"Testing at {rate} Hz - Speak into the mic...")
            status_label.show()
            test_button.setText("⏹ Stop")
            test_button.setStyleSheet(STOP_BUTTON_STYLE)
            test_timer.start(50)
            return stream
        except Exception:
            continue

    status_label.setText("Error: Could not open audio device")
    status_label.setStyleSheet("color: #f44336; font-size: 12px;")
    status_label.show()
    return None


def stop_mic_test(*, stream, vu_meter, status_label, test_button, test_timer):
    test_timer.stop()
    if stream is not None:
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass

    vu_meter.setValue(0)
    vu_meter.hide()
    status_label.hide()
    test_button.setText("🎤 Test")
    test_button.setStyleSheet(TEST_BUTTON_STYLE)
    return None


def update_vu_meter(vu_meter, amplitude: float) -> int:
    value = vu_value(amplitude)
    vu_meter.setValue(value)
    vu_meter.setStyleSheet(vu_style_for_value(value))
    return value
