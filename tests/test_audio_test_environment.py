"""Regression coverage for PortAudio initialization in headless test runners."""
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def _collect_with_sounddevice_failure(tmp_path, *, hardware=False, failure="PortAudioError"):
    (tmp_path / "sounddevice.py").write_text(
        f'class {failure}(Exception):\n    pass\n'
        f'raise {failure}("Error initializing PortAudio: PulseAudio cannot connect")\n',
        encoding="utf-8",
    )
    env = dict(os.environ, PYTHONPATH=os.pathsep.join((str(tmp_path), str(ROOT))),
               QT_QPA_PLATFORM="offscreen", PYTHONUNBUFFERED="1")
    command = [sys.executable, "-m", "pytest", "--collect-only", "-q",
               "tests/integration/test_audio_compression_service.py"]
    if hardware:
        command.append("--run-audio-hw")
    return subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, timeout=30)


def test_headless_collection_survives_portaudio_initialization_failure(tmp_path):
    result = _collect_with_sounddevice_failure(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "test_audio_compression_service" in result.stdout


def test_real_audio_run_reports_initialization_failure(tmp_path):
    result = _collect_with_sounddevice_failure(tmp_path, hardware=True)
    assert result.returncode != 0
    assert "PortAudio" in result.stdout + result.stderr


def test_unrelated_import_error_is_not_hidden(tmp_path):
    result = _collect_with_sounddevice_failure(tmp_path, failure="UnexpectedAudioError")
    assert result.returncode != 0
    assert "UnexpectedAudioError" in result.stdout + result.stderr


def test_fallback_reports_no_device_and_never_simulates_success(monkeypatch):
    import importlib
    import pytest
    from tests.conftest import _prepare_sounddevice

    error_type = type("PortAudioError", (Exception,), {"__module__": "sounddevice"})
    previous = sys.modules.get("sounddevice")
    monkeypatch.setitem(sys.modules, "sounddevice", previous)
    with monkeypatch.context() as patcher:
        def unavailable(_name):
            raise error_type("Error initializing PortAudio")
        patcher.setattr(importlib, "import_module", unavailable)
        with pytest.warns(RuntimeWarning, match="PortAudio could not initialize"):
            _prepare_sounddevice(run_audio_hw=False)
    fallback = sys.modules["sounddevice"]
    assert fallback.query_devices() == []
    with pytest.raises(RuntimeError, match="PortAudio unavailable"):
        fallback.InputStream()
