import pytest
from PyQt6.QtGui import QColor, QPalette

from src.ui.recording_in_progress.waveform import RealTimeWaveformVisualizer


@pytest.fixture
def waveform(qtbot):
    widget = RealTimeWaveformVisualizer()
    qtbot.addWidget(widget)
    widget.resize(400, 64)
    return widget


def test_history_scrolls_and_stays_bounded(waveform):
    assert not any(waveform.samples)
    for _ in range(100):
        waveform.add_amplitude(0.02)
    waveform.add_amplitude(0.05)
    assert len(waveform.samples) == 80
    assert list(waveform.samples) == [0.2] * 79 + [0.5]


@pytest.mark.parametrize('amplitude, expected', [(-1, 0), (0, 0), (0.025, 0.25), (2, 1), (float('nan'), 0), (float('inf'), 0)])
def test_normalizes_levels(waveform, amplitude, expected):
    waveform.add_amplitude(amplitude)
    assert waveform.samples[-1] == expected


@pytest.mark.parametrize('size', [(400, 64), (80, 48), (80, 2)])
def test_path_is_symmetric_and_within_widget(waveform, size):
    waveform.resize(*size)
    for level in [0, 1, 0.05] * 30:
        waveform.add_amplitude(level)
    bounds = waveform.waveform_path().boundingRect()
    if size[1] <= 4:
        assert waveform.waveform_path().isEmpty()
    else:
        assert waveform.rect().toRectF().contains(bounds)
        assert bounds.center().y() == pytest.approx(waveform.height() / 2)


def test_palette_and_signal_updates_change_rendered_image(waveform, qtbot):
    waveform.show()
    quiet = waveform.grab().toImage()
    waveform.add_amplitude(0.1)
    qtbot.waitUntil(lambda: waveform.grab().toImage() != quiet)
    first = waveform.grab().toImage()
    palette = waveform.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor('#121212'))
    palette.setColor(QPalette.ColorRole.Highlight, QColor('#ff00ff'))
    waveform.setPalette(palette)
    assert waveform.grab().toImage() != first
    assert waveform.grab().toImage().pixelColor(0, 0) == QColor('#121212')


def test_pause_decay_resume_and_cleanup(waveform, qtbot):
    waveform.add_amplitude(0.1)
    waveform.set_paused(True)
    waveform.add_amplitude(0.8)
    assert waveform.samples[-1] == 1
    qtbot.waitUntil(lambda: waveform.samples[-1] < 1)
    for _ in range(30):
        waveform._decay()
    assert not any(waveform.samples)
    assert not waveform.decay_timer.isActive()
    waveform.set_paused(False)
    waveform.add_amplitude(0.05)
    assert waveform.samples[-1] == 0.5
    waveform.set_paused(True)
    waveform.close()
    waveform.add_amplitude(1)
    assert not waveform.decay_timer.isActive()
    assert not any(waveform.samples)
