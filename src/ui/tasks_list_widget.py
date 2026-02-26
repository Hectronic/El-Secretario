# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from datetime import date, timedelta

from PyQt6.QtCore import Qt, QSettings, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QCheckBox,
    QComboBox,
    QMessageBox,
    QInputDialog,
    QFrame,
    QAbstractItemView,
    QApplication,
)
from src.ui.components import TaskRowWidget


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

    def __init__(self, db, limit=None, filter_date=None, record_id=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.limit = limit
        self.filter_date = filter_date
        self.record_id = record_id
        self.settings = QSettings("ElSecretario", "TasksTab")
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0 if self.filter_date else 10, 0 if self.filter_date else 10, 0 if self.filter_date else 10, 0 if self.filter_date else 10)

        if not self.filter_date and not self.record_id:
            title = QLabel("✅ Tasks")
            title.setStyleSheet("font-size: 24px; font-weight: bold; color: #607D8B;")
            layout.addWidget(title)

        controls = QHBoxLayout()
        self.count_label = QLabel("Loading...")
        controls.addWidget(self.count_label)
        controls.addStretch()

        self.order_combo = QComboBox()
        self.order_combo.addItem("Newest first", "date")
        self.order_combo.addItem("Custom order", "custom")
        saved_mode = self.settings.value(self.ORDER_MODE_KEY, "date")
        idx = self.order_combo.findData(saved_mode)
        self.order_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.order_combo.currentIndexChanged.connect(self._on_order_mode_changed)
        controls.addWidget(QLabel("Order:"))
        controls.addWidget(self.order_combo)

        self.show_completed_cb = QCheckBox("Show completed")
        self.show_completed_cb.setChecked(str(self.settings.value(self.SHOW_COMPLETED_KEY, "false")).lower() == "true")
        self.show_completed_cb.stateChanged.connect(self._on_show_completed_changed)
        controls.addWidget(self.show_completed_cb)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setProperty("class", "calendar-nav-btn")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh)
        controls.addWidget(self.refresh_btn)
        layout.addLayout(controls)

        self.tasks_list = ReorderableTasksList()
        self.tasks_list.setProperty("class", "embedded-list")
        self.tasks_list.setSpacing(4)
        self.tasks_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tasks_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.tasks_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.tasks_list.setDragEnabled(True)
        self.tasks_list.setAcceptDrops(True)
        self.tasks_list.setDropIndicatorShown(True)
        self.tasks_list.reordered.connect(self._on_list_reordered)
        self.tasks_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tasks_list)

        actions = QHBoxLayout()

        self.add_task_btn = QPushButton("Add Task")
        self.add_task_btn.setProperty("class", "calendar-nav-btn")
        self.add_task_btn.clicked.connect(self.open_create_dialog)
        actions.addWidget(self.add_task_btn)

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.setProperty("class", "calendar-nav-btn")
        self.select_all_btn.clicked.connect(self.tasks_list.selectAll)
        actions.addWidget(self.select_all_btn)

        self.clear_sel_btn = QPushButton("Clear Selection")
        self.clear_sel_btn.setProperty("class", "calendar-nav-btn")
        self.clear_sel_btn.clicked.connect(self.tasks_list.clearSelection)
        actions.addWidget(self.clear_sel_btn)

        self.complete_btn = QPushButton("Complete")
        self.complete_btn.setProperty("class", "calendar-nav-btn")
        self.complete_btn.clicked.connect(self._complete_selected)
        actions.addWidget(self.complete_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setProperty("class", "calendar-nav-btn")
        self.edit_btn.setStyleSheet("""
            QPushButton:disabled {
                background-color: #333;
                color: #666;
                border: 1px solid #444;
            }
        """)
        self.edit_btn.clicked.connect(self._edit_selected)
        actions.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setProperty("class", "calendar-nav-btn")
        self.delete_btn.clicked.connect(self._delete_selected)
        actions.addWidget(self.delete_btn)

        layout.addLayout(actions)

        self.tasks_list.itemSelectionChanged.connect(self._update_button_states)
        self._update_button_states()

        hint = QLabel("Drag rows to reorder when using 'Custom order'. Double-click to open source.")
        hint.setStyleSheet("color: #888888;")
        layout.addWidget(hint)

        self._apply_drag_mode()

    def open_create_dialog(self):
        content, ok = QInputDialog.getMultiLineText(self, "Create Task", "Task content:", "")
        if not ok or not content.strip():
            return
        notes, ok_notes = QInputDialog.getMultiLineText(self, "Task Notes", "Notes (optional):", "")
        if not ok_notes:
            return
        
        target_date = self.filter_date or date.today().isoformat()
        week_sunday = self.db._week_sunday(target_date) if hasattr(self.db, '_week_sunday') else None
        
        self.db.save_task(
            record_id=self.record_id,
            content=content.strip(),
            day_date=target_date if self.filter_date else (date.today().isoformat() if not self.record_id else None),
            week_start=week_sunday if not self.record_id else None,
            notes=notes.strip() or None,
        )
        self.tasks_changed.emit()
        self.refresh()

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

    def refresh(self):
        if self.record_id:
            tasks = self.db.get_tasks_by_record(self.record_id)
        elif self.filter_date:
            tags_filter = self.settings.value("last_tags_filter", None) # Could be passed from parent too
            tasks = self.db.get_tasks_by_date(self.filter_date, tags_filter, order_mode=self._current_order_mode())
        else:
            tasks = self.db.get_tasks_for_board(
                order_mode=self._current_order_mode(),
                include_completed=self.show_completed_cb.isChecked(),
                limit=self.limit,
            )
        self.tasks_list.clear()
        self.count_label.setText(f"{len(tasks)} task(s)")

        if not tasks:
            self.tasks_list.addItem("No tasks.")
            self._update_button_states()
            return

        for task in tasks:
            item = QListWidgetItem()
            # Ensure consistency with components metadata names
            task['source_type'] = task.get('record_type')
            
            item.setData(Qt.ItemDataRole.UserRole, task)
            self.tasks_list.addItem(item)

            row_widget = TaskRowWidget(task)
            row_widget.status_changed.connect(self._on_single_complete_toggle)
            
            item.setSizeHint(row_widget.sizeHint())
            self.tasks_list.setItemWidget(item, row_widget)
        
        self._update_button_states()

    def _update_button_states(self):
        selected_count = len(self.tasks_list.selectedItems())
        # Edit is only enabled if exactly one is selected
        self.edit_btn.setEnabled(selected_count == 1)
        # Delete and Complete are enabled if at least one is selected
        self.delete_btn.setEnabled(selected_count > 0)
        self.complete_btn.setEnabled(selected_count > 0)

    def _on_single_complete_toggle(self, task_id, is_completed):
        self.db.toggle_task_completion(task_id, is_completed)
        self.tasks_changed.emit()
        # Optionally notify other summary viewers if open
        self._notify_global_refresh()

    def _notify_global_refresh(self):
        for widget in QApplication.topLevelWidgets():
            if hasattr(widget, "refresh_tasks_sidebar"):
                widget.refresh_tasks_sidebar()

    def _complete_selected(self):
        selected_items = self.tasks_list.selectedItems()
        if not selected_items:
            item = self.tasks_list.currentItem()
            if not item: return
            selected_items = [item]
            
        for item in selected_items:
            task = item.data(Qt.ItemDataRole.UserRole)
            if not task: continue
            
            is_currently_completed = bool(task.get('is_completed', False))
            new_state = not is_currently_completed
            
            # Update DB
            self.db.toggle_task_completion(task['id'], new_state)
            
            # Update Widget UI
            widget = self.tasks_list.itemWidget(item)
            if isinstance(widget, TaskRowWidget):
                widget.set_completed(new_state)
            
            # Update data in item
            task['is_completed'] = new_state
            item.setData(Qt.ItemDataRole.UserRole, task)

        self.tasks_changed.emit()
        self._notify_global_refresh()

    def _edit_selected(self):
        selected_items = self.tasks_list.selectedItems()
        if not selected_items:
            item = self.tasks_list.currentItem()
            if not item: return
            selected_items = [item]
        
        item = selected_items[0]
        task = item.data(Qt.ItemDataRole.UserRole)
        if not task: return
        
        old_content = task.get('content', '')
        text, ok = QInputDialog.getMultiLineText(self, "Edit Task", "Task content:", old_content)
        if ok and text.strip():
            self.db.update_task_content(task['id'], text.strip())
            self.refresh()
            self.tasks_changed.emit()
            self._notify_global_refresh()

    def _delete_selected(self):
        selected_items = self.tasks_list.selectedItems()
        if not selected_items:
            item = self.tasks_list.currentItem()
            if not item: return
            selected_items = [item]
        
        if QMessageBox.question(self, "Delete Tasks", f"Delete {len(selected_items)} task(s)?") == QMessageBox.StandardButton.Yes:
            for item in selected_items:
                task = item.data(Qt.ItemDataRole.UserRole)
                if task:
                    self.db.delete_task(task['id'])
            self.refresh()
            self.tasks_changed.emit()
            self._notify_global_refresh()

    def _ordered_task_ids(self):
        ids = []
        for i in range(self.tasks_list.count()):
            task = self.tasks_list.item(i).data(Qt.ItemDataRole.UserRole)
            if isinstance(task, dict) and isinstance(task.get("id"), int):
                ids.append(int(task["id"]))
        return ids

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
            self.db.set_tasks_custom_order(ordered_ids)
            self.tasks_changed.emit()
            # Crucial: restore widgets that were lost during drag-drop move
            self.refresh()

    def _on_item_double_clicked(self, item):
        task = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(task, dict):
            return
        record_id = task.get("record_id")
        if isinstance(record_id, int):
            self.open_recording_requested.emit(record_id)
