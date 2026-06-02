# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from datetime import date, timedelta

from PyQt6.QtCore import Qt, QDate, QSettings, pyqtSignal
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
    QDialog,
    QDialogButtonBox,
    QTextEdit,
    QFrame,
    QMenu,
    QAbstractItemView,
    QApplication,
)
from src.ui.components import TaskRowWidget, TagsLineEdit


class ReorderableTasksList(QListWidget):
    reordered = pyqtSignal()

    def dropEvent(self, event):
        super().dropEvent(event)
        self.reordered.emit()


class TaskEditDialog(QDialog):
    """Unified modal for creating and editing tasks."""

    def __init__(self, db, parent=None, title="Task", task_data=None):
        super().__init__(parent)
        self.db = db
        self.task_data = task_data or {}
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(560, 360)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Task content"))
        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("Describe the task...")
        self.content_input.setMinimumHeight(110)
        self.content_input.setPlainText((self.task_data.get("content") or "").strip())
        layout.addWidget(self.content_input)

        layout.addWidget(QLabel("Notes (optional)"))
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Extra context, links, blockers...")
        self.notes_input.setMinimumHeight(90)
        self.notes_input.setPlainText((self.task_data.get("notes") or "").strip())
        layout.addWidget(self.notes_input)

        layout.addWidget(QLabel("Tags"))
        self.tags_input = TagsLineEdit()
        self.tags_input.set_tags(self.db.get_all_tags() if hasattr(self.db, "get_all_tags") else [])
        initial_tags = (self.task_data.get("tags") or "").strip()
        if not initial_tags and isinstance(self.task_data.get("record_id"), int):
            initial_tags = (self.task_data.get("record_tags") or "").strip()
        self.tags_input.setText(initial_tags)
        layout.addWidget(self.tags_input)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #f44336; font-size: 12px;")
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        if not self.get_content():
            self.error_label.setText("Task content is required.")
            self.content_input.setFocus()
            return
        self.accept()

    def get_content(self):
        return self.content_input.toPlainText().strip()

    def get_notes(self):
        notes = self.notes_input.toPlainText().strip()
        return notes or None

    def get_tags(self):
        tags = self.tags_input.text().strip()
        return tags or None


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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0 if self.filter_date else 10, 0 if self.filter_date else 10, 0 if self.filter_date else 10, 0 if self.filter_date else 10)

        if not self.filter_date and not self.record_id:
            title = QLabel("✅ Tasks")
            title.setStyleSheet("font-size: 24px; font-weight: bold; color: #607D8B;")
            layout.addWidget(title)

        controls = QHBoxLayout()
        self.controls_widget = QWidget()
        self.controls_widget.setLayout(controls)
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

        controls.addWidget(QLabel("Tag:"))
        self.tag_filter_combo = QComboBox()
        self.tag_filter_combo.setMinimumWidth(140)
        self.tag_filter_combo.currentIndexChanged.connect(self.refresh)
        controls.addWidget(self.tag_filter_combo)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setProperty("class", "calendar-nav-btn")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh)
        controls.addWidget(self.refresh_btn)
        layout.addWidget(self.controls_widget)

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
        self.tasks_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tasks_list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.tasks_list)

        actions = QHBoxLayout()
        self.actions_widget = QWidget()
        self.actions_widget.setLayout(actions)

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

        layout.addWidget(self.actions_widget)

        self.tasks_list.itemSelectionChanged.connect(self._update_button_states)
        self._update_button_states()

        hint = QLabel("Drag rows to reorder when using 'Custom order'. Double-click to open source.")
        hint.setStyleSheet("color: #888888;")
        self.hint_label = hint
        layout.addWidget(hint)

        self._apply_drag_mode()
        self._refresh_tag_filter_options()
        if not self.show_controls:
            self.controls_widget.setVisible(False)
            self.actions_widget.setVisible(False)
            self.hint_label.setVisible(False)
            self.tasks_list.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)

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

    def _date_to_iso(self, value):
        if value is None:
            return None
        if isinstance(value, QDate):
            return value.toString("yyyy-MM-dd") if value.isValid() else None
        if isinstance(value, date):
            return value.isoformat()
        text = str(value).strip()
        return text or None

    def _effective_tags_filter(self):
        if self.snapshot_mode and self.global_tags_filter:
            return self.global_tags_filter
        if self._has_global_context():
            return self.global_tags_filter
        local_tag = self.tag_filter_combo.currentText() if hasattr(self, "tag_filter_combo") else "All"
        if local_tag and local_tag != "All":
            return local_tag
        return None

    def open_create_dialog(self):
        dialog = TaskEditDialog(self.db, self, title="Create Task")
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        target_date = self.filter_date or date.today().isoformat()
        week_sunday = self.db._week_sunday(target_date) if hasattr(self.db, '_week_sunday') else None
        
        self.db.save_task(
            record_id=self.record_id,
            content=dialog.get_content(),
            tags=dialog.get_tags(),
            day_date=target_date if self.filter_date else (date.today().isoformat() if not self.record_id else None),
            week_start=week_sunday if not self.record_id else None,
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

        if week_monday:
            self.global_start_date = self._date_to_iso(week_monday)
            if date_filter:
                self.global_end_date = self._date_to_iso(date_filter)
            elif isinstance(week_monday, QDate):
                self.global_end_date = week_monday.addDays(6).toString("yyyy-MM-dd")
            elif isinstance(week_monday, date):
                self.global_end_date = (week_monday + timedelta(days=6)).isoformat()
            else:
                self.global_end_date = self.global_start_date
        elif date_filter:
            self.global_start_date = self._date_to_iso(date_filter)
            self.global_end_date = self.global_start_date
        else:
            self.global_start_date = None
            self.global_end_date = None

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
        if self.snapshot_mode in ("day_created", "day_completed"):
            day_ref = self.snapshot_ref or self.filter_date
            snapshot = self.db.get_daily_task_snapshot(day_ref, tags_filter) if day_ref else {}
            if self.snapshot_mode == "day_created":
                tasks = snapshot.get("created_this_day", [])
            else:
                tasks = snapshot.get("completed_this_day", [])
        elif self.snapshot_mode in ("week_created", "week_completed", "week_pending_before"):
            week_ref = self.snapshot_ref
            snapshot = self.db.get_weekly_task_snapshot(week_ref, tags_filter) if week_ref else {}
            mapping = {
                "week_created": "created_this_week",
                "week_completed": "completed_this_week",
                "week_pending_before": "pending_from_before",
            }
            tasks = snapshot.get(mapping.get(self.snapshot_mode, ""), [])
        elif self.record_id:
            tasks = self.db.get_tasks_by_record(self.record_id)
            if tags_filter:
                filtered = []
                for t in tasks:
                    if isinstance(t.get("record_id"), int):
                        tags_text = str(t.get("record_tags") or t.get("tags") or "")
                    else:
                        tags_text = str(t.get("tags") or t.get("record_tags") or "")
                    if tags_filter in [x.strip() for x in tags_text.split(",") if x.strip()]:
                        filtered.append(t)
                tasks = filtered
        elif self.filter_date:
            tasks = self.db.get_tasks_by_date(self.filter_date, tags_filter, order_mode=self._current_order_mode())
        elif self.global_start_date and self.global_end_date:
            tasks = self.db.get_tasks_by_date_range(
                self.global_start_date,
                self.global_end_date,
                tags_filter=tags_filter,
                order_mode=self._current_order_mode(),
                include_completed=self.show_completed_cb.isChecked(),
            )
        else:
            tasks = self.db.get_tasks_for_board(
                order_mode=self._current_order_mode(),
                include_completed=self.show_completed_cb.isChecked(),
                limit=self.limit,
            )
            if tags_filter:
                filtered = []
                for t in tasks:
                    if isinstance(t.get("record_id"), int):
                        tags_text = str(t.get("record_tags") or t.get("tags") or "")
                    else:
                        tags_text = str(t.get("tags") or t.get("record_tags") or "")
                    if tags_filter in [x.strip() for x in tags_text.split(",") if x.strip()]:
                        filtered.append(t)
                tasks = filtered
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

    def _selected_task_items(self):
        task_items = []
        for item in self.tasks_list.selectedItems():
            task = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(task, dict) and isinstance(task.get("id"), int):
                task_items.append(item)
        return task_items

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
        for item in items:
            task = item.data(Qt.ItemDataRole.UserRole)
            if not task:
                continue
            self.db.toggle_task_completion(task['id'], completed_state)
            widget = self.tasks_list.itemWidget(item)
            if isinstance(widget, TaskRowWidget):
                widget.set_completed(completed_state)
            task['is_completed'] = completed_state
            item.setData(Qt.ItemDataRole.UserRole, task)
        self._emit_tasks_mutated(refresh_self=True)

    def _edit_task_item(self, item):
        task = item.data(Qt.ItemDataRole.UserRole)
        if not task:
            return
        dialog = TaskEditDialog(self.db, self, title="Edit Task", task_data=task)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.db.update_task_details(
                task["id"],
                dialog.get_content(),
                dialog.get_notes(),
                dialog.get_tags(),
            )
            self._emit_tasks_mutated(refresh_self=True)

    def _delete_items(self, items):
        if QMessageBox.question(self, "Delete Tasks", f"Delete {len(items)} task(s)?") != QMessageBox.StandardButton.Yes:
            return
        for item in items:
            task = item.data(Qt.ItemDataRole.UserRole)
            if task:
                self.db.delete_task(task['id'])
        self._emit_tasks_mutated(refresh_self=True)

    def _on_single_complete_toggle(self, task_id, is_completed):
        self.db.toggle_task_completion(task_id, is_completed)
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
        selected_items = self._selected_task_items()
        if not selected_items:
            item = self.tasks_list.currentItem()
            if not item: return
            task = item.data(Qt.ItemDataRole.UserRole)
            if not isinstance(task, dict):
                return
            selected_items = [item]
        selected_tasks = [it.data(Qt.ItemDataRole.UserRole) for it in selected_items]
        all_completed = all(bool(t.get("is_completed")) for t in selected_tasks if isinstance(t, dict))
        self._set_completion_for_items(selected_items, not all_completed)

    def _edit_selected(self):
        selected_items = self._selected_task_items()
        if not selected_items:
            item = self.tasks_list.currentItem()
            if not item: return
            task = item.data(Qt.ItemDataRole.UserRole)
            if not isinstance(task, dict):
                return
            selected_items = [item]
        self._edit_task_item(selected_items[0])

    def _delete_selected(self):
        selected_items = self._selected_task_items()
        if not selected_items:
            item = self.tasks_list.currentItem()
            if not item: return
            task = item.data(Qt.ItemDataRole.UserRole)
            if not isinstance(task, dict):
                return
            selected_items = [item]
        self._delete_items(selected_items)

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
            # Crucial: restore widgets that were lost during drag-drop move
            self._emit_tasks_mutated(refresh_self=True)

    def _on_item_double_clicked(self, item):
        task = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(task, dict):
            return
        record_id = task.get("record_id")
        if isinstance(record_id, int):
            self.open_recording_requested.emit(record_id)
