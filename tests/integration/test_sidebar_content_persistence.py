from unittest.mock import MagicMock

from PyQt6.QtWidgets import QCheckBox, QComboBox, QLineEdit, QListWidget, QMainWindow, QTabWidget

from src.database import DBManager
from src.notebook_database import NotebookDBManager
from src.ui.main_window.sidebar_content import SidebarContentCoordinator


class _SidebarWindow(QMainWindow):
    def __init__(self, db, notebook_db):
        super().__init__()
        self.db = db
        self.notebook_db = notebook_db
        self.history_list = QListWidget()
        self.collections_list = QListWidget()
        self.notebooks_list = QListWidget()
        self.sessions_list = QListWidget()
        self.central_tabs = QTabWidget()
        self.tag_filter_combo = QComboBox()
        self.tag_filter_combo.addItem("All")
        self.fav_filter_cb = QCheckBox()
        self.search_input = QLineEdit()
        self.current_week_monday = None
        self.current_date_filter = None
        self.welcome_widget = None
        self.rag = None
        self.open_chat_tab = MagicMock()

    def filter_history_list(self, text):
        self.coordinator.filter_history_list(text)

    def on_favorite_toggled(self, record_id, checked):
        self.coordinator.on_favorite_toggled(record_id, checked)

    def delete_recording(self, record_id):
        self.coordinator.delete_recording(record_id)


def test_sidebar_content_reads_real_record_and_notebook_stores(qtbot, tmp_path):
    db = DBManager(str(tmp_path / "sidebar.sqlite"))
    record_id = db.save("planning.wav", "Transcript", 10.0, "Planning")
    db.update_tags(record_id, "planning")
    notebook_db = NotebookDBManager(str(tmp_path / "notebooks.sqlite"))
    notebook_id = notebook_db.create_notebook("Research")
    notebook_db.add_text_entry(notebook_id, "Persisted notebook entry")
    window = _SidebarWindow(db, notebook_db)
    window.coordinator = SidebarContentCoordinator(window)
    qtbot.addWidget(window)

    window.coordinator.load_history()
    window.coordinator.load_collections()
    window.coordinator.load_notebooks()
    window.coordinator.open_notebook_chat(notebook_id, "Research")

    assert window.history_list.count() == 1
    assert window.collections_list.item(0).text() == "planning"
    assert window.notebooks_list.item(0).text() == "📓 Research"
    window.open_chat_tab.assert_called_once_with(
        initial_contexts=[{"type": "notebook", "value": notebook_id, "label": "Research"}]
    )
