from src.ui.batch_process.actions import transcription_request
from src.ui.batch_process.state import BatchQueueState, batch_task_token


def test_batch_queue_state_counts_each_terminal_task_once():
    state = BatchQueueState()
    state.reset([4])
    task = {"source": "batch_process", "type": "transcription", "record_id": 4, "title": "a.wav"}

    assert state.register_enqueued(task)
    assert state.register_terminal(task)
    assert state.register_transcription_terminal(task)
    assert not state.register_terminal(task)
    assert state.active_tasks == 0
    assert state.processed_count == 1
    assert batch_task_token(task)[1] == 4


def test_transcription_request_keeps_queue_contract():
    request = transcription_request(
        {"id": 8, "filename": "capture.wav"},
        recordings_dir="/tmp/recordings",
        model="large-v3",
    )

    assert request == {
        "record_id": 8,
        "file_path": "/tmp/recordings/capture.wav",
        "model_size": "large-v3",
        "language": None,
        "diarization": True,
        "title": "capture.wav",
        "source": "batch_process",
    }


def test_transcription_request_preserves_a_windows_queue_path_contract():
    request = transcription_request(
        {"id": 8, "filename": "capture.wav"},
        recordings_dir=r"C:\recordings",
        model="large-v3",
    )

    assert request["file_path"] == r"C:\recordings\capture.wav"
