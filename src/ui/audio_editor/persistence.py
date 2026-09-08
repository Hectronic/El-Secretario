"""Safe persistence of edited audio files and their recording metadata."""

import os
import shutil

import soundfile as sf


def apply_edited_audio(path, audio, sample_rate, db, record_id):
    """Back up the source once, write edited audio, and persist its duration."""
    backup_path = f"{path}.orig"
    if not os.path.exists(backup_path):
        shutil.copy2(path, backup_path)
    sf.write(path, audio, sample_rate)
    duration = float(len(audio) / sample_rate)
    db.update_duration(record_id, duration)
    return duration
