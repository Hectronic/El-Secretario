from src.ui.recording_in_progress.session import (
    build_finished_config,
    format_elapsed_time,
    save_last_run_config,
)


class _Settings:
    def __init__(self):
        self.values = {}

    def setValue(self, key, value):
        self.values[key] = value


def test_finished_config_normalizes_user_input_and_preserves_capture_options():
    result = build_finished_config(
        {"device_index": 2, "capture_system_audio": True},
        title="  Planning  ",
        tags=" work, ops ",
        recording_notes="  Decide release date.  ",
        pending_tasks=["Publish notes"],
        model="large-v3",
        diarization=1,
        auto_summarize_after_transcription=True,
    )

    assert result == {
        "device_index": 2,
        "capture_system_audio": True,
        "title": "Planning",
        "tags": "work, ops",
        "recording_notes": "Decide release date.",
        "pending_tasks": ["Publish notes"],
        "model": "large-v3",
        "diarization": True,
        "auto_summarize_after_transcription": True,
    }
    assert format_elapsed_time(125) == "02:05"


def test_save_last_run_config_persists_capture_preferences():
    settings = _Settings()

    save_last_run_config(
        settings,
        model="medium",
        diarization=True,
        auto_summarize_after_transcription=False,
    )

    assert settings.values == {
        "rec_config/model": "medium",
        "rec_config/diarization": True,
        "rec_config/auto_summarize_after_transcription": False,
    }
