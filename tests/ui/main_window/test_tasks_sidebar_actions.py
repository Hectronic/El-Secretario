import sys
from unittest.mock import MagicMock

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QApplication, QListWidget, QWidget

from src.ui.main_window import tasks_sidebar_actions as module
from src.ui.main_window.tasks_sidebar_actions import TasksSidebarActionsCoordinator


_APP = None


def _app():
    global _APP
    _APP = QApplication.instance() or _APP or QApplication(sys.argv)
    _APP.setQuitOnLastWindowClosed(False)
    return _APP


class _Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class _TaskWidget(QWidget):
    def __init__(self, *_args, **_kwargs):
        super().__init__()
        self.completion_toggled = _Signal()

    def sizeHint(self):
        return QSize(200, 40)


class _Action:
    def __init__(self):
        self.enabled = True

    def setEnabled(self, enabled):
        self.enabled = bool(enabled)


class _Menu:
    next_choice_label = None

    def __init__(self, *_args, **_kwargs):
        self.actions = []

    def addAction(self, label):
        action = _Action()
        self.actions.append((label, action))
        return action

    def exec(self, _point):
        for label, action in self.actions:
            if label == self.next_choice_label:
                return action
        return None


class _Item:
    def __init__(self, task):
        self._task = task
        self._font = MagicMock()

    def data(self, role):
        return self._task if role == Qt.ItemDataRole.UserRole else None

    def checkState(self):
        return Qt.CheckState.Checked if self._task.get("is_completed") else Qt.CheckState.Unchecked

    def font(self):
        return self._font

    def setFont(self, font):
        self._font = font

    def setForeground(self, _fg):
        pass


class _Window:
    def __init__(self):
        self.tasks_sidebar_list = QListWidget()
        self.db = MagicMock()
        self.tasks_sidebar_limit = 20
        self.current_week_monday = None
        self.current_date_filter = None
        self.tag_filter_combo = MagicMock()
        self.tag_filter_combo.currentText.return_value = "All"
        self.on_task_sidebar_item_changed = MagicMock()
        self.refresh_tasks_sidebar = MagicMock()
        self.open_recording_tab = MagicMock()


def test_refresh_tasks_sidebar_populates_items(monkeypatch):
    _app()
    monkeypatch.setattr(module, "SidebarTaskCompactWidget", _TaskWidget)
    coordinator = TasksSidebarActionsCoordinator(_Window())
    coordinator.window.db.get_recent_incomplete_tasks.return_value = [
        {"id": 1, "content": "Task", "tags": "a", "record_id": None, "is_completed": 0}
    ]

    coordinator.refresh_tasks_sidebar()
    assert coordinator.window.tasks_sidebar_list.count() == 1


def test_on_task_sidebar_item_changed_toggles(monkeypatch):
    _app()
    coordinator = TasksSidebarActionsCoordinator(_Window())
    item = _Item({"id": 5, "is_completed": 1})
    coordinator.on_task_sidebar_item_changed(item)
    coordinator.window.db.toggle_task_completion.assert_called_once_with(5, True)


def test_show_tasks_sidebar_context_menu_delete(monkeypatch):
    _app()
    monkeypatch.setattr(module, "QMenu", _Menu)
    mock_box = MagicMock()
    mock_box.question.return_value = mock_box.StandardButton.Yes
    monkeypatch.setattr(module, "QMessageBox", mock_box)
    coordinator = TasksSidebarActionsCoordinator(_Window())
    task = {"id": 9, "record_id": 1, "is_completed": 0}
    item = MagicMock()
    item.data.return_value = task
    coordinator.window.tasks_sidebar_list.itemAt = MagicMock(return_value=item)
    _Menu.next_choice_label = "Delete"

    coordinator.show_tasks_sidebar_context_menu(QPoint(0, 0))
    coordinator.window.db.delete_task.assert_called_once_with(9)
