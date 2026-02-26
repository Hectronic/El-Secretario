import sys
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication

def test_mainwindow_init():
    app = QApplication(sys.argv)
    
    with patch('src.ui.main_window.Recorder'), \
         patch('src.ui.main_window.DBManager'), \
         patch('src.ui.recording_in_progress_widget.DBManager'), \
         patch('src.ui.recording_widget.DBManager'), \
         patch('src.rag_engine.RAGEngine'), \
         patch('src.ui.recording_widget.QMediaPlayer'), \
         patch('src.ui.recording_widget.QAudioOutput'):
        
        from src.ui.main_window import MainWindow
        print("Instantiating MainWindow...")
        window = MainWindow()
        print("MainWindow instantiated successfully.")
        window.close()

if __name__ == "__main__":
    test_mainwindow_init()
