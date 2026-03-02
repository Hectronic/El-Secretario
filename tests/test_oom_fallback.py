import pytest
import os
import torch
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import QCoreApplication
from src.worker import TranscriberThread

# Mocking WhisperModel to simulate OOM
class MockWhisperModel:
    def __init__(self, model_size, device, compute_type, **kwargs):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        
        # Simulate CUDA OOM on the first attempt if device is cuda
        if device == "cuda" and not getattr(MockWhisperModel, "_fallback_happened", False):
            MockWhisperModel._fallback_happened = True
            raise RuntimeError("CUDA failed with error out of memory")
    
    def transcribe(self, audio_path, **kwargs):
        # Mock segments: just one segment for testing
        mock_segment = MagicMock()
        mock_segment.text = "Mocked transcription text"
        mock_segment.start = 0.0
        mock_segment.end = 1.0
        return [mock_segment], MagicMock()

@pytest.fixture
def app(qtbot):
    """Ensure a QCoreApplication exists."""
    return QCoreApplication.instance() or QCoreApplication([])

def test_transcriber_thread_oom_fallback(app, tmp_path):
    # Reset the flag
    MockWhisperModel._fallback_happened = False
    
    # Create a dummy audio file
    dummy_audio = tmp_path / "test.wav"
    dummy_audio.write_bytes(b"dummy data")
    
    # Force TranscriberThread to start with cuda (mocking torch.cuda.is_available)
    with patch("torch.cuda.is_available", return_value=True), \
         patch("src.worker.WhisperModel", side_effect=MockWhisperModel), \
         patch("src.worker.os.path.getsize", return_value=100):
        
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
        assert MockWhisperModel._fallback_happened is True
        assert thread.device == "cpu"
        assert thread.force_cpu is True
        assert "CUDA OOM detected. Falling back to CPU..." in status_updates
        assert len(finished_results) == 1
        assert finished_results[0]["text"] == "Mocked transcription text"
        print("\nOOM Fallback Test Passed Successfully!")

if __name__ == "__main__":
    # If running directly, we might need a dummy app
    pass
