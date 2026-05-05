import os
import sys
import tempfile
import types
import warnings
from pathlib import Path

import pytest


# Force headless Qt unless explicitly overridden by the environment.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("EL_SECRETARIO_SKIP_AUDIO_ENUM", "1")
# Keep third-party telemetry and progress monitors quiet during tests.
# These background threads have been a source of intermittent native aborts.
os.environ.setdefault("POSTHOG_DISABLED", "1")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("TQDM_DISABLE", "1")

# Some third-party packages still initialize background workers even when the
# environment flags are set. Stub or hard-disable them before tests import code.
if "posthog" not in sys.modules:
    posthog_stub = types.ModuleType("posthog")
    posthog_stub.disabled = True
    posthog_stub.project_api_key = ""
    posthog_stub.capture = lambda *args, **kwargs: None
    sys.modules["posthog"] = posthog_stub

try:
    import tqdm

    tqdm.tqdm.monitor_interval = 0
except Exception:
    pass


_SWIG_DEPRECATION_MESSAGES = (
    r"builtin type SwigPyPacked has no __module__ attribute",
    r"builtin type SwigPyObject has no __module__ attribute",
    r"builtin type swigvarlink has no __module__ attribute",
)


def _suppress_third_party_swig_warnings():
    # sentencepiece emits these Python 3.12 deprecations while loading native
    # SWIG types. Keep the filter narrow so application deprecations still fail.
    for message in _SWIG_DEPRECATION_MESSAGES:
        warnings.filterwarnings(
            "ignore",
            message=message,
            category=DeprecationWarning,
        )


_suppress_third_party_swig_warnings()
_QSETTINGS_TEMP_DIR = None


def pytest_configure(config):
    _suppress_third_party_swig_warnings()
    _isolate_qsettings_user_scope()


def pytest_unconfigure(config):
    global _QSETTINGS_TEMP_DIR
    if _QSETTINGS_TEMP_DIR is not None:
        _QSETTINGS_TEMP_DIR.cleanup()
        _QSETTINGS_TEMP_DIR = None


def _isolate_qsettings_user_scope():
    """Keep tests from writing application settings into the real user config."""
    global _QSETTINGS_TEMP_DIR
    if _QSETTINGS_TEMP_DIR is not None:
        return
    from PyQt6.QtCore import QSettings

    _QSETTINGS_TEMP_DIR = tempfile.TemporaryDirectory(prefix="secretario_qsettings_")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        _QSETTINGS_TEMP_DIR.name,
    )


def pytest_runtest_setup(item):
    _suppress_third_party_swig_warnings()


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
    has_audio_input = _has_input_audio_device() if run_audio_hw else False

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
