import pytest
from unittest.mock import patch
from PyQt6.QtCore import QCoreApplication
from src.worker_components.transcriber_thread import TranscriberThread

@pytest.fixture
def app(qtbot):
    """Ensure a QCoreApplication exists."""
    return QCoreApplication.instance() or QCoreApplication([])

def test_transcriber_thread_oom_fallback(app, tmp_path):
    # Create a dummy audio file
    dummy_audio = tmp_path / "test.wav"
    dummy_audio.write_bytes(b"dummy data")
    
    # Force TranscriberThread to start with cuda. The subprocess should fail once
    # with OOM and then retry on CPU.
    with patch("torch.cuda.is_available", return_value=True), \
         patch("src.worker_components.transcriber_thread.platform.system", return_value="Linux"), \
         patch("src.worker_components.transcriber_thread._run_transcription_in_subprocess") as mock_run_subprocess, \
         patch("src.worker_components.transcriber_thread.os.path.getsize", return_value=100):

        mock_run_subprocess.side_effect = [
            RuntimeError("CUDA failed with error out of memory"),
            [{"start": 0.0, "end": 1.0, "text": "Mocked transcription text"}],
        ]
        
        # Create thread
        thread = TranscriberThread(
            str(dummy_audio), 
            model_size="base", 
            device="cuda", 
            compute_type="int8"
        )
        
        # Track signals
        finished_results = []
        status_updates = []
        
        thread.finished.connect(lambda res: finished_results.append(res))
        thread.status_update.connect(lambda val: status_updates.append(val))
        
        # Run thread logic synchronously for easier testing or use qtbot
        thread.run()
        
        # Assertions
        assert thread.device == "cpu"
        assert thread.force_cpu is True
        assert any("Retrying after crash" in msg for msg in status_updates)
        assert len(finished_results) == 1
        assert finished_results[0]["text"] == "Mocked transcription text"
        assert mock_run_subprocess.call_count == 2
        print("\nOOM Fallback Test Passed Successfully!")

if __name__ == "__main__":
    # If running directly, we might need a dummy app
    pass
