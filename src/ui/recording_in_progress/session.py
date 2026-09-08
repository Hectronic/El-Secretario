"""Pure session-state helpers for in-progress recordings."""


def format_elapsed_time(duration_seconds):
    minutes = duration_seconds // 60
    seconds = duration_seconds % 60
    return f"{minutes:02}:{seconds:02}"


def build_finished_config(
    initial_config,
    *,
    title,
    tags,
    recording_notes,
    pending_tasks,
    model,
    diarization,
    auto_summarize_after_transcription,
):
    """Build the stable payload consumed by the recording-tab coordinator."""
    return {
        **initial_config,
        "title": title.strip(),
        "tags": tags.strip(),
        "recording_notes": recording_notes.strip(),
        "pending_tasks": list(pending_tasks),
        "model": model,
        "diarization": bool(diarization),
        "auto_summarize_after_transcription": bool(auto_summarize_after_transcription),
    }


def save_last_run_config(settings, *, model, diarization, auto_summarize_after_transcription):
    settings.setValue("rec_config/model", model)
    settings.setValue("rec_config/diarization", bool(diarization))
    settings.setValue(
        "rec_config/auto_summarize_after_transcription",
        bool(auto_summarize_after_transcription),
    )
