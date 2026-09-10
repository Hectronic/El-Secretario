# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from PyQt6.QtCore import Qt, QSettings, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QCheckBox,
    QComboBox,
    QMessageBox,
    QDialog,
    QMenu,
    QAbstractItemView,
    QApplication,
)
from src.ui.tasks.actions import (
    create_manual_task,
    delete_tasks,
    save_custom_order,
    set_task_completion,
    update_task_details,
)
from src.ui.tasks.edit_dialog import TaskEditDialog
from src.ui.tasks.filters import (
    fetch_task_board_tasks,
    resolve_effective_tags_filter,
    resolve_global_date_range,
)
from src.ui.tasks.presentation import (
    apply_completion_state,
    ordered_task_ids,
    render_task_rows,
    selected_or_current_task_items,
    selected_task_items,
)
from src.ui.tasks.board_view import build_task_board_view


class ReorderableTasksList(QListWidget):
    reordered = pyqtSignal()

    def dropEvent(self, event):
        super().dropEvent(event)
        self.reordered.emit()


class TasksListWidget(QWidget):
    """Tasks board with rows, ordering and bulk actions."""

    open_recording_requested = pyqtSignal(int)
    tasks_changed = pyqtSignal()

    ORDER_MODE_KEY = "tasks_tab/order_mode"
    SHOW_COMPLETED_KEY = "tasks_tab/show_completed"

    def __init__(
        self,
        db,
        limit=None,
        filter_date=None,
        record_id=None,
        parent=None,
        show_controls=True,
        snapshot_mode=None,
        snapshot_ref=None,
    ):
        super().__init__(parent)
        self.db = db
        self.limit = limit
        self.filter_date = filter_date
        self.record_id = record_id
        self.show_controls = show_controls
        self.snapshot_mode = snapshot_mode
        self.snapshot_ref = snapshot_ref
        self.global_start_date = None
        self.global_end_date = None
        self.global_tags_filter = None
        self.settings = QSettings("ElSecretario", "TasksTab")
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        """Build the visual shell through the focused board-view owner."""
        build_task_board_view(self, ReorderableTasksList)

    def _refresh_tag_filter_options(self):
        if not hasattr(self, "tag_filter_combo"):
            return
        current = self.tag_filter_combo.currentText() or "All"
        tags = self.db.get_all_tags() if hasattr(self.db, "get_all_tags") else []
        self.tag_filter_combo.blockSignals(True)
        self.tag_filter_combo.clear()
        self.tag_filter_combo.addItem("All")
        for tag in tags:
            self.tag_filter_combo.addItem(tag)
        idx = self.tag_filter_combo.findText(current)
        self.tag_filter_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.tag_filter_combo.blockSignals(False)

    def _has_global_context(self):
        return bool(self.global_start_date and self.global_end_date)

    def _effective_tags_filter(self):
        local_tag = self.tag_filter_combo.currentText() if hasattr(self, "tag_filter_combo") else "All"
        return resolve_effective_tags_filter(
            snapshot_mode=self.snapshot_mode,
            global_start_date=self.global_start_date,
            global_end_date=self.global_end_date,
            global_tags_filter=self.global_tags_filter,
            local_tag=local_tag,
        )

    def open_create_dialog(self):
        dialog = TaskEditDialog(self.db, self, title="Create Task")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        create_manual_task(
            self.db,
            record_id=self.record_id,
            content=dialog.get_content(),
            tags=dialog.get_tags(),
            filter_date=self.filter_date,
            notes=dialog.get_notes(),
        )
        self._emit_tasks_mutated(refresh_self=True)

    def _current_order_mode(self):
        return str(self.order_combo.currentData() or "date")

    def _apply_drag_mode(self):
        # We always allow internal move to enable reordering
        self.tasks_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

    def _on_order_mode_changed(self):
        self.settings.setValue(self.ORDER_MODE_KEY, self._current_order_mode())
        self._apply_drag_mode()
        self.refresh()

    def _on_show_completed_changed(self):
        self.settings.setValue(self.SHOW_COMPLETED_KEY, "true" if self.show_completed_cb.isChecked() else "false")
        self.refresh()

    def set_global_filters(self, week_monday=None, date_filter=None, tags_filter=None):
        """Apply global calendar filters for the main Tasks tab and refresh."""
        if self.record_id is not None or self.filter_date is not None:
            return

        self.global_start_date, self.global_end_date = resolve_global_date_range(
            week_monday, date_filter
        )

        self.global_tags_filter = tags_filter or None
        if hasattr(self, "tag_filter_combo"):
            self._refresh_tag_filter_options()
            if self._has_global_context():
                self.tag_filter_combo.blockSignals(True)
                if self.global_tags_filter:
                    idx = self.tag_filter_combo.findText(self.global_tags_filter)
                    self.tag_filter_combo.setCurrentIndex(idx if idx >= 0 else 0)
                else:
                    self.tag_filter_combo.setCurrentIndex(0)
                self.tag_filter_combo.blockSignals(False)
                self.tag_filter_combo.setEnabled(False)
            else:
                self.tag_filter_combo.setEnabled(True)
        self.refresh()

    def refresh(self):
        self._refresh_tag_filter_options()
        tags_filter = self._effective_tags_filter()
        tasks = fetch_task_board_tasks(
            self.db,
            snapshot_mode=self.snapshot_mode,
            snapshot_ref=self.snapshot_ref,
            record_id=self.record_id,
            filter_date=self.filter_date,
            limit=self.limit,
            global_start_date=self.global_start_date,
            global_end_date=self.global_end_date,
            tags_filter=tags_filter,
            order_mode=self._current_order_mode(),
            include_completed=self.show_completed_cb.isChecked(),
        )
        task_count = render_task_rows(
            self.tasks_list, tasks, self._on_single_complete_toggle
        )
        self.count_label.setText(f"{task_count} task(s)")
        self._update_button_states()

    def _update_button_states(self):
        selected_count = len(self.tasks_list.selectedItems())
        # Edit is only enabled if exactly one is selected
        self.edit_btn.setEnabled(selected_count == 1)
        # Delete and Complete are enabled if at least one is selected
        self.delete_btn.setEnabled(selected_count > 0)
        self.complete_btn.setEnabled(selected_count > 0)

    def _selected_task_items(self):
        return selected_task_items(self.tasks_list)

    def _show_context_menu(self, pos):
        clicked_item = self.tasks_list.itemAt(pos)
        if clicked_item:
            task = clicked_item.data(Qt.ItemDataRole.UserRole)
            if isinstance(task, dict):
                if clicked_item not in self.tasks_list.selectedItems():
                    self.tasks_list.clearSelection()
                    clicked_item.setSelected(True)

        selected_items = self._selected_task_items()
        if not selected_items:
            return

        selected_tasks = [it.data(Qt.ItemDataRole.UserRole) for it in selected_items]
        all_completed = all(bool(t.get("is_completed")) for t in selected_tasks)

        menu = QMenu(self)
        complete_action = menu.addAction("Mark as pending" if all_completed else "Mark as completed")
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")
        go_action = menu.addAction("Go to recording")

        edit_action.setEnabled(len(selected_items) == 1)
        record_id = None
        if len(selected_items) == 1:
            record_id = selected_tasks[0].get("record_id")
        go_action.setEnabled(isinstance(record_id, int))

        chosen = menu.exec(self.tasks_list.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == complete_action:
            self._set_completion_for_items(selected_items, not all_completed)
        elif chosen == edit_action and len(selected_items) == 1:
            self._edit_task_item(selected_items[0])
        elif chosen == delete_action:
            self._delete_items(selected_items)
        elif chosen == go_action and isinstance(record_id, int):
            self.open_recording_requested.emit(record_id)

    def _set_completion_for_items(self, items, completed_state: bool):
        task_ids = [
            task["id"]
            for item in items
            if isinstance((task := item.data(Qt.ItemDataRole.UserRole)), dict)
        ]
        set_task_completion(self.db, task_ids, completed_state)
        apply_completion_state(self.tasks_list, items, completed_state)
        self._emit_tasks_mutated(refresh_self=True)

    def _edit_task_item(self, item):
        task = item.data(Qt.ItemDataRole.UserRole)
        if not task:
            return
        dialog = TaskEditDialog(self.db, self, title="Edit Task", task_data=task)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            update_task_details(
                self.db,
                task["id"],
                dialog.get_content(),
                dialog.get_notes(),
                dialog.get_tags(),
            )
            self._emit_tasks_mutated(refresh_self=True)

    def _delete_items(self, items):
        if QMessageBox.question(self, "Delete Tasks", f"Delete {len(items)} task(s)?") != QMessageBox.StandardButton.Yes:
            return
        delete_tasks(
            self.db,
            [task["id"] for item in items if (task := item.data(Qt.ItemDataRole.UserRole))],
        )
        self._emit_tasks_mutated(refresh_self=True)

    def _on_single_complete_toggle(self, task_id, is_completed):
        set_task_completion(self.db, [task_id], is_completed)
        self._emit_tasks_mutated(refresh_self=False)

    def _emit_tasks_mutated(self, refresh_self: bool):
        self.tasks_changed.emit()
        self._notify_global_refresh()
        if refresh_self:
            self.refresh()

    def _notify_global_refresh(self):
        for widget in QApplication.topLevelWidgets():
            if hasattr(widget, "refresh_tasks_sidebar"):
                widget.refresh_tasks_sidebar()

    def _complete_selected(self):
        selected_items = selected_or_current_task_items(self.tasks_list)
        if not selected_items:
            return
        selected_tasks = [it.data(Qt.ItemDataRole.UserRole) for it in selected_items]
        all_completed = all(bool(t.get("is_completed")) for t in selected_tasks if isinstance(t, dict))
        self._set_completion_for_items(selected_items, not all_completed)

    def _edit_selected(self):
        selected_items = selected_or_current_task_items(self.tasks_list)
        if not selected_items:
            return
        self._edit_task_item(selected_items[0])

    def _delete_selected(self):
        selected_items = selected_or_current_task_items(self.tasks_list)
        if not selected_items:
            return
        self._delete_items(selected_items)

    def _ordered_task_ids(self):
        return ordered_task_ids(self.tasks_list)

    def _on_list_reordered(self):
        # Force custom mode if they reordered
        if self._current_order_mode() != "custom":
            self.order_combo.blockSignals(True)
            self.order_combo.setCurrentIndex(self.order_combo.findData("custom"))
            self.settings.setValue(self.ORDER_MODE_KEY, "custom")
            self._apply_drag_mode()
            self.order_combo.blockSignals(False)

        ordered_ids = self._ordered_task_ids()
        if ordered_ids:
            save_custom_order(self.db, ordered_ids)
            # Crucial: restore widgets that were lost during drag-drop move
            self._emit_tasks_mutated(refresh_self=True)

    def _on_item_double_clicked(self, item):
        task = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(task, dict):
            return
        record_id = task.get("record_id")
        if isinstance(record_id, int):
            self.open_recording_requested.emit(record_id)
