import sys
import os
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
import wave

def test_recording_flow_logic():
    app = QApplication(sys.argv)
    
    # Create dummy wav
    dummy_wav = "/tmp/test_audio_debug.wav"
    with wave.open(dummy_wav, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(b'\x00' * 1024)

    with patch('src.ui.main_window.Recorder') as MockRecorder, \
         patch('src.ui.main_window.DBManager') as MockDB, \
         patch('src.ui.recording_in_progress_widget.DBManager'), \
         patch('src.ui.recording_widget.DBManager'), \
         patch('src.rag_engine.RAGEngine'), \
         patch('src.ui.recording_widget.QMediaPlayer'), \
         patch('src.ui.recording_widget.QAudioOutput'):
        
        MockRecorder.return_value.stop.return_value = dummy_wav
        MockDB.return_value.save.return_value = 123
        MockDB.return_value.fetch_record.return_value = {
            'id': 123, 'title': 'Test', 'filename': 'test.wav', 
            'transcription': '', 'summary': '', 'tags': '', 
            'created_at': '2026-02-18', 'duration': 10.0, 'is_diarized': 0, 'type': 'recording'
        }

        from src.ui.main_window import MainWindow
        print("Instantiating MainWindow...")
        window = MainWindow()
        
        print("Starting new recording...")
        window.start_new_recording({})
        
        from src.ui.recording_in_progress_widget import RecordingInProgressWidget
        rec_in_progress = window.central_tabs.currentWidget()
        if not isinstance(rec_in_progress, RecordingInProgressWidget):
            print(f"Error: expected RecordingInProgressWidget, got {type(rec_in_progress)}")
            return

        print("Finishing recording...")
        # This will trigger on_recording_finished -> open_recording_tab
        with patch.object(window, 'load_history'): # Avoid sidebar refresh issues
            rec_in_progress.finish_recording()
        
        print("Checking transition...")
        new_widget = window.central_tabs.currentWidget()
        from src.ui.recording_widget import RecordingWidget
        if isinstance(new_widget, RecordingWidget):
            print("Successfully transitioned to RecordingWidget.")
        else:
            print(f"Error: expected RecordingWidget, got {type(new_widget)}")

        window.close()
    
    if os.path.exists(dummy_wav):
        os.remove(dummy_wav)

if __name__ == "__main__":
    test_recording_flow_logic()
