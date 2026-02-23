import os
from pathlib import Path

import pytest


# Force headless Qt unless explicitly overridden by the environment.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def pytest_addoption(parser):
    parser.addoption(
        "--run-audio-hw",
        action="store_true",
        default=False,
        help="Run tests that require real audio input hardware.",
    )


def _has_input_audio_device() -> bool:
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        return any(dev.get("max_input_channels", 0) > 0 for dev in devices)
    except Exception:
        return False


def pytest_collection_modifyitems(config, items):
    run_audio_hw = config.getoption("--run-audio-hw")
    has_audio_input = _has_input_audio_device()

    marker_by_file = {
        "test_shutdown_cleanup_stress.py": ("stress", "ui"),
        "test_batch_reliability.py": ("stress",),
        "test_recording_flow.py": ("ui",),
        "test_tab_context_menu.py": ("ui",),
        "test_recording_widget_ui.py": ("ui",),
        "test_calendar_ui.py": ("ui",),
        "test_calendar_button.py": ("ui",),
    }

    for item in items:
        filename = Path(str(item.fspath)).name

        for mark in marker_by_file.get(filename, ()):
            item.add_marker(getattr(pytest.mark, mark))

        if item.get_closest_marker("audio_hw"):
            if not run_audio_hw:
                item.add_marker(
                    pytest.mark.skip(reason="requires --run-audio-hw")
                )
            elif not has_audio_input:
                item.add_marker(
                    pytest.mark.skip(reason="no input audio device detected")
                )
