"""Qt composition for the task-board shell."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractItemView, QCheckBox, QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


def build_task_board_view(widget, reorderable_list_type):
    """Build and wire the visual controls owned by a task-board facade."""
    layout = QVBoxLayout(widget)
    margin = 0 if widget.filter_date else 10
    layout.setContentsMargins(margin, margin, margin, margin)
    if not widget.filter_date and not widget.record_id:
        title = QLabel("✅ Tasks"); title.setStyleSheet("font-size: 24px; font-weight: bold; color: #607D8B;"); layout.addWidget(title)
    controls = QHBoxLayout(); widget.controls_widget = QWidget(); widget.controls_widget.setLayout(controls)
    widget.count_label = QLabel("Loading..."); controls.addWidget(widget.count_label); controls.addStretch()
    widget.order_combo = QComboBox(); widget.order_combo.addItem("Newest first", "date"); widget.order_combo.addItem("Custom order", "custom")
    index = widget.order_combo.findData(widget.settings.value(widget.ORDER_MODE_KEY, "date")); widget.order_combo.setCurrentIndex(index if index >= 0 else 0); widget.order_combo.currentIndexChanged.connect(widget._on_order_mode_changed)
    controls.addWidget(QLabel("Order:")); controls.addWidget(widget.order_combo)
    widget.show_completed_cb = QCheckBox("Show completed"); widget.show_completed_cb.setChecked(str(widget.settings.value(widget.SHOW_COMPLETED_KEY, "false")).lower() == "true"); widget.show_completed_cb.stateChanged.connect(widget._on_show_completed_changed); controls.addWidget(widget.show_completed_cb)
    controls.addWidget(QLabel("Tag:")); widget.tag_filter_combo = QComboBox(); widget.tag_filter_combo.setMinimumWidth(140); widget.tag_filter_combo.currentIndexChanged.connect(widget.refresh); controls.addWidget(widget.tag_filter_combo)
    widget.refresh_btn = QPushButton("Refresh"); widget.refresh_btn.setProperty("class", "calendar-nav-btn"); widget.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor); widget.refresh_btn.clicked.connect(widget.refresh); controls.addWidget(widget.refresh_btn); layout.addWidget(widget.controls_widget)
    widget.tasks_list = reorderable_list_type(); widget.tasks_list.setProperty("class", "embedded-list"); widget.tasks_list.setSpacing(4); widget.tasks_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection); widget.tasks_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove); widget.tasks_list.setDefaultDropAction(Qt.DropAction.MoveAction); widget.tasks_list.setDragEnabled(True); widget.tasks_list.setAcceptDrops(True); widget.tasks_list.setDropIndicatorShown(True); widget.tasks_list.reordered.connect(widget._on_list_reordered); widget.tasks_list.itemDoubleClicked.connect(widget._on_item_double_clicked); widget.tasks_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); widget.tasks_list.customContextMenuRequested.connect(widget._show_context_menu); layout.addWidget(widget.tasks_list)
    actions = QHBoxLayout(); widget.actions_widget = QWidget(); widget.actions_widget.setLayout(actions)
    for attr, text, slot in (("add_task_btn", "Add Task", widget.open_create_dialog), ("select_all_btn", "Select All", widget.tasks_list.selectAll), ("clear_sel_btn", "Clear Selection", widget.tasks_list.clearSelection), ("complete_btn", "Complete", widget._complete_selected), ("edit_btn", "Edit", widget._edit_selected), ("delete_btn", "Delete", widget._delete_selected)):
        button = QPushButton(text); button.setProperty("class", "calendar-nav-btn"); button.clicked.connect(slot); setattr(widget, attr, button); actions.addWidget(button)
    layout.addWidget(widget.actions_widget); widget.tasks_list.itemSelectionChanged.connect(widget._update_button_states); widget._update_button_states()
    widget.hint_label = QLabel("Drag rows to reorder when using 'Custom order'. Double-click to open source."); widget.hint_label.setStyleSheet("color: #888888;"); layout.addWidget(widget.hint_label)
    widget._apply_drag_mode(); widget._refresh_tag_filter_options()
    if not widget.show_controls:
        widget.controls_widget.setVisible(False); widget.actions_widget.setVisible(False); widget.hint_label.setVisible(False); widget.tasks_list.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
