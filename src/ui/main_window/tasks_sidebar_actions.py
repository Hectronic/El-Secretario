# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QDialog, QListWidgetItem, QMenu, QMessageBox

from src.ui.components import SidebarTaskCompactWidget
from src.ui.tasks_list_widget import TaskEditDialog


class TasksSidebarActionsCoordinator:
    """Own tasks sidebar list rendering and task item actions."""

    def __init__(self, window):
        self.window = window

    def refresh_tasks_sidebar(self):
        if not hasattr(self.window, "tasks_sidebar_list"):
            return

        self.window.tasks_sidebar_list.blockSignals(True)
        self.window.tasks_sidebar_list.clear()
        tag = self.window.tag_filter_combo.currentText() if hasattr(self.window, "tag_filter_combo") else "All"
        tags_filter = tag if tag and tag != "All" else None

        if self.window.current_week_monday and self.window.current_date_filter:
            tasks = self.window.db.get_tasks_by_date_range(
                self.window.current_week_monday.toString("yyyy-MM-dd"),
                self.window.current_date_filter,
                tags_filter=tags_filter,
                include_completed=False,
            )
            if self.window.tasks_sidebar_limit is not None:
                tasks = tasks[:self.window.tasks_sidebar_limit]
        elif self.window.current_date_filter:
            tasks = self.window.db.get_tasks_by_date(
                self.window.current_date_filter,
                tags_filter=tags_filter,
            )
            tasks = [task for task in tasks if not bool(task.get("is_completed"))]
            if self.window.tasks_sidebar_limit is not None:
                tasks = tasks[:self.window.tasks_sidebar_limit]
        else:
            tasks = self.window.db.get_recent_incomplete_tasks(limit=self.window.tasks_sidebar_limit)

        if not tasks:
            self.window.tasks_sidebar_list.addItem("No incomplete tasks.")
            self.window.tasks_sidebar_list.blockSignals(False)
            return

        for task in tasks:
            if isinstance(task.get("record_id"), int):
                tags = (task.get("record_tags") or task.get("tags") or "").strip()
            else:
                tags = (task.get("tags") or task.get("record_tags") or "").strip()
            content = (task.get("content") or "").strip() or "Untitled task"
            if len(content) > 72:
                content = content[:69].rstrip() + "..."

            tag_values = [t.strip() for t in tags.split(",") if t.strip()]

            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, task)
            self.window.tasks_sidebar_list.addItem(item)
            widget = SidebarTaskCompactWidget(
                content,
                tag_values,
                task_id=task.get("id"),
                is_completed=bool(task.get("is_completed")),
                parent=self.window.tasks_sidebar_list,
            )
            widget.completion_toggled.connect(self._toggle_sidebar_task_completion)
            item.setSizeHint(widget.sizeHint())
            self.window.tasks_sidebar_list.setItemWidget(item, widget)

        try:
            self.window.tasks_sidebar_list.itemChanged.disconnect(self.window.on_task_sidebar_item_changed)
        except Exception:
            pass
        self.window.tasks_sidebar_list.itemChanged.connect(self.window.on_task_sidebar_item_changed)
        self.window.tasks_sidebar_list.blockSignals(False)

    def _toggle_sidebar_task_completion(self, task_id, is_completed):
        if not isinstance(task_id, int):
            return
        self.window.db.toggle_task_completion(task_id, bool(is_completed))
        self.window.refresh_tasks_sidebar()

    def on_task_sidebar_item_changed(self, item):
        task = item.data(Qt.ItemDataRole.UserRole)
        if not task:
            return

        is_completed = item.checkState() == Qt.CheckState.Checked
        self.window.db.toggle_task_completion(task["id"], is_completed)

        font = item.font()
        font.setStrikeOut(is_completed)
        item.setFont(font)
        if is_completed:
            item.setForeground(Qt.GlobalColor.gray)
        else:
            item.setForeground(QApplication.palette().text())

    def show_tasks_sidebar_context_menu(self, point):
        item = self.window.tasks_sidebar_list.itemAt(point)
        if not item:
            return
        task = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(task, dict):
            return

        menu = QMenu(self.window)
        is_completed = bool(task.get("is_completed"))
        complete_action = menu.addAction("Mark as pending" if is_completed else "Mark as completed")
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")
        go_action = menu.addAction("Go to recording")
        go_action.setEnabled(isinstance(task.get("record_id"), int))

        chosen = menu.exec(self.window.tasks_sidebar_list.viewport().mapToGlobal(point))
        if chosen is None:
            return
        if chosen == complete_action:
            self.window.db.toggle_task_completion(task["id"], not is_completed)
            self.window.refresh_tasks_sidebar()
        elif chosen == edit_action:
            dialog = TaskEditDialog(self.window.db, self.window, title="Edit Task", task_data=task)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.window.db.update_task_details(
                    task["id"],
                    dialog.get_content(),
                    dialog.get_notes(),
                    dialog.get_tags(),
                )
                self.window.refresh_tasks_sidebar()
        elif chosen == delete_action:
            if QMessageBox.question(self.window, "Delete Task", "Delete this task?") == QMessageBox.StandardButton.Yes:
                self.window.db.delete_task(task["id"])
                self.window.refresh_tasks_sidebar()
        elif chosen == go_action and isinstance(task.get("record_id"), int):
            self.window.open_recording_tab(task["record_id"])
