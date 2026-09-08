"""Collection and notebook content behavior for the main sidebar."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QInputDialog, QLabel, QListWidget, QListWidgetItem, QMenu, QMessageBox, QVBoxLayout, QWidget

from src.ui.notebook_widget import NotebookWidget
from src.ui.notebooks_list_widget import NotebooksListWidget


class SidebarOrganizationCoordinator:
    """Own collection and notebook lists, tabs, dialogs, and chat context entry."""

    def __init__(self, window):
        self.window = window

    def load_collections(self):
        if not hasattr(self.window, "collections_list"):
            return
        self.window.collections_list.clear()
        tags = self.window.db.get_all_tags()
        if not tags:
            self.window.collections_list.addItem("No tags.")
            return
        for tag in tags:
            item = QListWidgetItem(tag)
            item.setData(Qt.ItemDataRole.UserRole, tag)
            self.window.collections_list.addItem(item)

    def load_notebooks(self):
        self.window.notebooks_list.clear()
        for notebook in self.window.notebook_db.get_notebooks()[:5]:
            item = QListWidgetItem(f"📓 {notebook['name']}")
            item.setData(Qt.ItemDataRole.UserRole, notebook["id"])
            self.window.notebooks_list.addItem(item)

    def open_collections_list(self):
        for index in range(self.window.central_tabs.count()):
            if self.window.central_tabs.tabText(index) == "Colecciones":
                self.window.central_tabs.setCurrentIndex(index)
                return
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.addWidget(QLabel("<h2>🏷️ Todas las Colecciones</h2>"))
        tags = self.window.db.get_all_tags()
        if not tags:
            layout.addWidget(QLabel("No hay colecciones aún. Añade tags a tus grabaciones."))
        else:
            list_widget = QListWidget()
            list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            for tag in tags:
                item = QListWidgetItem(f"🏷️ {tag}")
                item.setData(Qt.ItemDataRole.UserRole, tag)
                list_widget.addItem(item)
            list_widget.itemClicked.connect(lambda item: self.window.open_collection_tab(item.data(Qt.ItemDataRole.UserRole)))
            layout.addWidget(list_widget)
        layout.addStretch()
        index = self.window.central_tabs.addTab(widget, "Colecciones")
        self.window.central_tabs.setCurrentIndex(index)

    def open_notebooks_list(self):
        for index in range(self.window.central_tabs.count()):
            if isinstance(self.window.central_tabs.widget(index), NotebooksListWidget):
                self.window.central_tabs.setCurrentIndex(index)
                return
        notebook_list = NotebooksListWidget(self.window.notebook_db)
        notebook_list.notebook_opened.connect(self.window.open_notebook)
        notebook_list.chat_requested.connect(self.window.open_notebook_chat)
        index = self.window.central_tabs.addTab(notebook_list, "Libretas")
        self.window.central_tabs.setCurrentIndex(index)

    def open_notebook(self, notebook_id, name):
        for index in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(index)
            if isinstance(widget, NotebookWidget) and widget.notebook_id == notebook_id:
                self.window.central_tabs.setCurrentIndex(index)
                return
        notebook = NotebookWidget(self.window.notebook_db, notebook_id, name, self.window.recorder)
        notebook.chat_requested.connect(self.window.open_notebook_chat)
        index = self.window.central_tabs.addTab(notebook, f"📓 {name}")
        self.window.central_tabs.setCurrentIndex(index)

    def open_notebook_chat(self, notebook_id, notebook_name):
        self.window.open_chat_tab(initial_contexts=[{"type": "notebook", "value": notebook_id, "label": notebook_name}])

    def _find_notebook_by_id(self, notebook_id):
        return next((notebook for notebook in self.window.notebook_db.get_notebooks() if notebook.get("id") == notebook_id), None)

    def create_notebook(self):
        name, accepted = QInputDialog.getText(self.window, "New Notebook", "Notebook Name:")
        if accepted and name.strip():
            self.window.notebook_db.create_notebook(name.strip())
            self.window.load_notebooks()

    def rename_notebook(self, notebook_id):
        notebook = self._find_notebook_by_id(notebook_id)
        if not notebook:
            return
        name, accepted = QInputDialog.getText(self.window, "Rename Notebook", "New Name:", text=notebook["name"])
        if accepted and name.strip():
            self.window.notebook_db.rename_notebook(notebook_id, name.strip())
            self.window.load_notebooks()

    def delete_notebook(self, notebook_id):
        notebook = self._find_notebook_by_id(notebook_id)
        if not notebook:
            return
        reply = QMessageBox.question(self.window, "Delete Notebook", f"Are you sure you want to delete '{notebook['name']}' and all its notes?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.window.notebook_db.delete_notebook(notebook_id)
            self.window.load_notebooks()

    def show_notebooks_sidebar_context_menu(self, point):
        item = self.window.notebooks_list.itemAt(point)
        if not item:
            return
        notebook_id = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(notebook_id, int):
            return
        notebook_name = item.text().replace("📓 ", "")
        menu = QMenu(self.window)
        open_action = menu.addAction("Open")
        chat_action = menu.addAction("Chat")
        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")
        chosen = menu.exec(self.window.notebooks_list.viewport().mapToGlobal(point))
        if chosen == open_action:
            self.window.open_notebook(notebook_id, notebook_name)
        elif chosen == chat_action:
            self.window.open_notebook_chat(notebook_id, notebook_name)
        elif chosen == rename_action:
            self.rename_notebook(notebook_id)
        elif chosen == delete_action:
            self.delete_notebook(notebook_id)
