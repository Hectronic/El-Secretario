from pathlib import Path

import numpy as np
import soundfile as sf

from src.audio import AudioCompressionService
from src.database import DBManager


def _wav(path: Path):
    sf.write(path, np.zeros(16000, dtype=np.float32), 16000)


def test_service_emits_qt_completion_after_sqlite_swap(qtbot, tmp_path):
    source = tmp_path / "capture.wav"
    _wav(source)
    db = DBManager(str(tmp_path / "compression.sqlite"))
    record_id = db.save(source.name, "", 1.0, "Capture")
    service = AudioCompressionService()

    def encoder(path):
        target = Path(path).with_suffix(".mp3")
        target.write_bytes(b"compressed")
        return str(target)

    job = service.start_compression(str(source), record_id, db, encoder=encoder)
    job.release_source()

    with qtbot.waitSignal(service.compression_finished, timeout=3000) as emitted:
        job.thread.join(timeout=2)

    assert emitted.args == [record_id, str(source.with_suffix(".mp3"))]
    assert db.fetch_record(record_id)["filename"] == "capture.mp3"
    assert not source.exists()
