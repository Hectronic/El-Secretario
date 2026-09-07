from unittest.mock import MagicMock

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidget, QTabWidget

from src.ui.main_window.sidebar_organization import SidebarOrganizationCoordinator


def test_organization_populates_collections_and_emits_notebook_chat_context(qtbot):
    window = MagicMock()
    window.collections_list = QListWidget()
    window.notebooks_list = QListWidget()
    window.central_tabs = QTabWidget()
    window.db.get_all_tags.return_value = ["planning"]
    window.notebook_db.get_notebooks.return_value = [{"id": 4, "name": "Research"}]
    qtbot.addWidget(window.collections_list)
    qtbot.addWidget(window.notebooks_list)
    coordinator = SidebarOrganizationCoordinator(window)

    coordinator.load_collections()
    coordinator.load_notebooks()
    coordinator.open_notebook_chat(4, "Research")

    assert window.collections_list.item(0).data(Qt.ItemDataRole.UserRole) == "planning"
    assert window.notebooks_list.item(0).data(Qt.ItemDataRole.UserRole) == 4
    window.open_chat_tab.assert_called_once_with(
        initial_contexts=[{"type": "notebook", "value": 4, "label": "Research"}]
    )
