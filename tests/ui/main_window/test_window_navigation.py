from unittest.mock import MagicMock

from src.ui.main_window.window_navigation import MainWindowNavigationCoordinator


class _Item:
    def __init__(self, value, text):
        self.value = value
        self.label = text

    def data(self, _role):
        return self.value

    def text(self):
        return self.label


def test_notebook_and_collection_clicks_open_matching_content():
    window = MagicMock()
    coordinator = MainWindowNavigationCoordinator(window)

    coordinator.on_notebook_clicked(_Item(7, "📓 Research"))
    coordinator.on_collection_clicked(_Item("work", "work"))
    coordinator.on_collection_clicked(_Item(None, "No tags."))

    window.open_notebook.assert_called_once_with(7, "Research")
    window.open_collection_tab.assert_called_once_with("work")


def test_selected_tag_chat_uses_tag_context_or_an_empty_chat():
    window = MagicMock()
    coordinator = MainWindowNavigationCoordinator(window)

    window.collections_list.currentItem.return_value = _Item("work", "work")
    coordinator.open_selected_tag_chat()
    window.open_collection_chat.assert_called_once_with("work")

    window.reset_mock()
    window.collections_list.currentItem.return_value = None
    coordinator.open_selected_tag_chat()
    window.open_chat_tab.assert_called_once_with(None)


def test_tag_filter_change_refreshes_history_and_active_tabs():
    window = MagicMock()

    MainWindowNavigationCoordinator(window).on_tag_filter_changed("work")

    window.request_sidebar_reload.assert_called_once_with(include_history=True)
    window.sync_active_tabs.assert_called_once_with()
