"""Small sidebar navigation decisions owned outside the MainWindow shell."""

from PyQt6.QtCore import Qt


class MainWindowNavigationCoordinator:
    def __init__(self, window):
        self.window = window

    def on_notebook_clicked(self, item):
        notebook_id = item.data(Qt.ItemDataRole.UserRole)
        notebook_name = item.text().replace("📓 ", "")
        self.window.open_notebook(notebook_id, notebook_name)

    def on_collection_clicked(self, item):
        tag = item.data(Qt.ItemDataRole.UserRole) or item.text()
        if tag and tag != "No tags.":
            self.window.open_collection_tab(tag)

    def open_selected_tag_chat(self):
        item = self.window.collections_list.currentItem()
        if item is None:
            self.window.open_chat_tab(None)
            return

        tag = item.data(Qt.ItemDataRole.UserRole) or item.text()
        if not tag or tag == "No tags.":
            self.window.open_chat_tab(None)
            return
        self.window.open_collection_chat(tag)

    def open_collection_chat(self, tag):
        self.window.open_chat_tab(
            initial_contexts=[{"type": "tag", "value": tag, "label": tag}]
        )

    def on_tag_filter_changed(self, _tag):
        self.window.request_sidebar_reload(include_history=True)
        self.window.sync_active_tabs()
