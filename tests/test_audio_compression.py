import os
import shutil
import time
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from src.audio import AudioCompressionJob, Recorder, compress_wav_to_mp3
from src.database import DBManager


def _wav(path: Path, seconds: float = 3.0):
    samples = np.sin(np.linspace(0, seconds * 600, int(16000 * seconds))).astype(np.float32)
    sf.write(path, samples, 16000)


def _wait_for(path: Path, timeout: float = 5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return
        time.sleep(0.01)
    raise AssertionError(f"Timed out waiting for {path}")


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg is not available")
def test_compress_wav_to_mp3_uses_readable_mono_voice_profile(tmp_path):
    source = tmp_path / "meeting.wav"
    _wav(source)
    original_size = source.stat().st_size

    target = Path(compress_wav_to_mp3(str(source)))

    assert target.suffix == ".mp3"
    assert target.exists()
    assert source.exists()
    assert target.stat().st_size < original_size * 0.30
    assert Recorder.get_duration(str(target)) == 3.0
    info = sf.info(target)
    assert info.channels == 1
    assert info.samplerate == 16000


def test_background_job_keeps_wav_until_transcription_releases_source(tmp_path):
    source = tmp_path / "meeting.wav"
    _wav(source)
    db = DBManager(str(tmp_path / "compression.sqlite"))
    record_id = db.save(source.name, "", 0.0, "Meeting")
    target = source.with_suffix(".mp3")

    def encoder(path):
        target_path = Path(path).with_suffix(".mp3")
        target_path.write_bytes(b"compressed")
        return str(target_path)

    job = AudioCompressionJob(str(source), record_id, db, encoder=encoder).start()
    _wait_for(target)

    assert source.exists()
    assert db.fetch_record(record_id)["filename"] == "meeting.wav"

    job.release_source()
    job.thread.join(timeout=5)

    assert not job.thread.is_alive()
    assert not source.exists()
    assert db.fetch_record(record_id)["filename"] == "meeting.mp3"


def test_background_job_preserves_wav_and_database_on_encoder_failure(tmp_path):
    source = tmp_path / "meeting.wav"
    _wav(source)
    db = DBManager(str(tmp_path / "compression.sqlite"))
    record_id = db.save(source.name, "", 0.0, "Meeting")
    errors = []

    def failing_encoder(_path):
        raise RuntimeError("encoder unavailable")

    job = AudioCompressionJob(
        str(source), record_id, db, encoder=failing_encoder, on_error=lambda *_args: errors.append(_args)
    ).start()
    job.thread.join(timeout=5)

    assert not job.thread.is_alive()
    assert source.exists()
    assert db.fetch_record(record_id)["filename"] == "meeting.wav"
    assert errors == [(record_id, "encoder unavailable")]
