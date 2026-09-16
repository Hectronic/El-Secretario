
import sys
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication
from src.ui.tasks_list_widget import TasksListWidget

def test_minimal():
    app = QApplication(sys.argv)
    db = MagicMock()
    # Mocking get_tasks_for_board to return empty list
    db.get_tasks_for_board.return_value = []
    print("Instantiating TasksListWidget...")
    widget = TasksListWidget(db)
    print("TasksListWidget instantiated successfully.")
    
if __name__ == "__main__":
    test_minimal()
