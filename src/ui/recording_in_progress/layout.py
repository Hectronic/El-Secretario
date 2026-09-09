"""Visual composition and responsive density for active recording."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.ui.component_widgets.tags import TagsLineEdit
from src.transcription_options import (
    DEFAULT_TRANSCRIPTION_MODEL,
    get_transcription_model_options,
    normalize_transcription_model,
)


def build_recording_in_progress_layout(widget):
    root_layout = QVBoxLayout(widget)
    root_layout.setContentsMargins(0, 0, 0, 0)

    widget.scroll_area = QScrollArea()
    widget.scroll_area.setWidgetResizable(True)
    widget.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
    widget.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    root_layout.addWidget(widget.scroll_area)
    content = QWidget()
    widget.scroll_area.setWidget(content)
    layout = QVBoxLayout(content)
    layout.setContentsMargins(20, 14, 20, 14)
    layout.setSpacing(14)
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    widget.main_content_layout = layout

    widget.status_label = QLabel("Recording in Progress...")
    widget.status_label.setStyleSheet("font-size: 24px; color: #f44336; font-weight: bold;")
    layout.addWidget(widget.status_label, alignment=Qt.AlignmentFlag.AlignHCenter)
    widget.timer_label = QLabel("00:00")
    widget.timer_label.setStyleSheet("font-size: 64px; font-weight: bold; color: #eeeeee;")
    layout.addWidget(widget.timer_label, alignment=Qt.AlignmentFlag.AlignHCenter)
    widget.vu_meter = QProgressBar()
    widget.vu_meter.setRange(0, 100)
    widget.vu_meter.setTextVisible(False)
    widget.vu_meter.setFixedSize(400, 20)
    widget.vu_meter.setStyleSheet("QProgressBar { border: 2px solid #555; border-radius: 5px; background-color: #333; } QProgressBar::chunk { background-color: #f44336; width: 10px; }")
    layout.addWidget(widget.vu_meter, alignment=Qt.AlignmentFlag.AlignHCenter)

    controls_layout = QHBoxLayout()
    controls_layout.setSpacing(12)
    controls_layout.setContentsMargins(0, 4, 0, 4)
    controls_layout.addStretch(1)
    widget.pause_btn = QPushButton("Pause")
    widget.pause_btn.setProperty("class", "calendar-nav-btn")
    widget.pause_btn.setFixedSize(124, 50)
    widget.pause_btn.clicked.connect(widget.toggle_pause)
    controls_layout.addWidget(widget.pause_btn)
    widget.stop_btn = QPushButton("Finish")
    widget.stop_btn.setProperty("class", "calendar-primary-btn")
    widget.stop_btn.setFixedSize(124, 50)
    widget.stop_btn.clicked.connect(widget.finish_recording)
    controls_layout.addWidget(widget.stop_btn)
    widget.cancel_btn = QPushButton("Cancel")
    widget.cancel_btn.setProperty("class", "record-del-btn")
    widget.cancel_btn.setFixedSize(124, 50)
    widget.cancel_btn.clicked.connect(widget.cancel_recording)
    controls_layout.addWidget(widget.cancel_btn)
    controls_layout.addStretch(1)
    layout.addLayout(controls_layout)

    widget.options_group = QGroupBox("Recording Options")
    options_layout = QFormLayout()
    options_layout.setSpacing(10)
    widget.title_input = QLineEdit()
    widget.title_input.setPlaceholderText("Enter recording title...")
    options_layout.addRow("Title:", widget.title_input)
    widget.tags_input = TagsLineEdit()
    widget.tags_input.set_tags(widget.db.get_all_tags())
    options_layout.addRow("Tags:", widget.tags_input)
    widget.model_combo = QComboBox()
    widget.model_combo.addItems(get_transcription_model_options())
    widget.model_combo.setCurrentText(normalize_transcription_model(widget.config.get("model", DEFAULT_TRANSCRIPTION_MODEL)))
    options_layout.addRow("Model:", widget.model_combo)
    widget.diarization_check = QCheckBox("Enable speaker diarization")
    widget.diarization_check.setToolTip("Enable speaker diarization (Requires HF Token)")
    widget.diarization_check.setChecked(widget.config.get("diarization", False))
    options_layout.addRow("", widget.diarization_check)
    default_auto_summary = widget.settings.value("rec_config/auto_summarize_after_transcription", False, type=bool)
    widget.auto_summary_check = QCheckBox("Summarize automatically after transcription")
    widget.auto_summary_check.setToolTip("Queues an AI summary as soon as transcription is done")
    widget.auto_summary_check.setChecked(widget.config.get("auto_summarize_after_transcription", default_auto_summary))
    options_layout.addRow("", widget.auto_summary_check)
    widget.model_combo.currentTextChanged.connect(widget._save_last_run_config)
    widget.diarization_check.toggled.connect(widget._save_last_run_config)
    widget.auto_summary_check.toggled.connect(widget._save_last_run_config)
    widget.options_group.setLayout(options_layout)
    layout.addWidget(widget.options_group)

    widget.workspace_split = QSplitter(Qt.Orientation.Horizontal)
    widget.notes_group = QGroupBox("Notes")
    notes_layout = QVBoxLayout(widget.notes_group)
    widget.notes_input = QTextEdit()
    widget.notes_input.setPlaceholderText("Write important context while recording...")
    widget.notes_input.setMinimumHeight(220)
    notes_layout.addWidget(widget.notes_input)
    widget.workspace_split.addWidget(widget.notes_group)
    widget.tasks_group = QGroupBox("Quick Tasks")
    tasks_layout = QVBoxLayout(widget.tasks_group)
    quick_add = QHBoxLayout()
    widget.task_input = QLineEdit()
    widget.task_input.setPlaceholderText("Add actionable task and press Add...")
    widget.task_input.returnPressed.connect(widget.add_quick_task)
    widget.add_task_btn = QPushButton("Add")
    widget.add_task_btn.clicked.connect(widget.add_quick_task)
    quick_add.addWidget(widget.task_input, 1)
    quick_add.addWidget(widget.add_task_btn)
    tasks_layout.addLayout(quick_add)
    widget.quick_tasks_list = QListWidget()
    widget.quick_tasks_list.setAlternatingRowColors(True)
    tasks_layout.addWidget(widget.quick_tasks_list, 1)
    quick_actions = QHBoxLayout()
    widget.remove_task_btn = QPushButton("Remove Selected")
    widget.remove_task_btn.clicked.connect(widget.remove_selected_quick_task)
    widget.clear_tasks_btn = QPushButton("Clear All")
    widget.clear_tasks_btn.clicked.connect(widget.quick_tasks_list.clear)
    quick_actions.addWidget(widget.remove_task_btn)
    quick_actions.addWidget(widget.clear_tasks_btn)
    quick_actions.addStretch()
    tasks_layout.addLayout(quick_actions)
    widget.workspace_split.addWidget(widget.tasks_group)
    widget.workspace_split.setSizes([1, 1])
    layout.addWidget(widget.workspace_split, 1)
    apply_layout_density(widget, widget._is_windows)


def apply_layout_density(widget, is_windows, viewport_height=None):
    if viewport_height is None:
        viewport_height = widget.scroll_area.viewport().height() if widget.scroll_area.viewport() else widget.height()
    compact_mode = viewport_height > 0 and viewport_height < (900 if is_windows else 780)
    if compact_mode == widget._compact_mode_active:
        return
    widget._compact_mode_active = compact_mode
    if compact_mode:
        widget.main_content_layout.setContentsMargins(14, 8, 14, 8)
        widget.main_content_layout.setSpacing(10)
        widget.status_label.setStyleSheet("font-size: 20px; color: #f44336; font-weight: bold;")
        widget.timer_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #eeeeee;")
        widget.vu_meter.setFixedSize(320, 16)
        widget.notes_input.setMinimumHeight(160)
        widget.pause_btn.setFixedSize(112, 44)
        widget.stop_btn.setFixedSize(112, 44)
        widget.cancel_btn.setFixedSize(112, 44)
        widget.workspace_split.setOrientation(Qt.Orientation.Vertical)
        return
    widget.main_content_layout.setContentsMargins(20, 14, 20, 14)
    widget.main_content_layout.setSpacing(14)
    widget.status_label.setStyleSheet("font-size: 24px; color: #f44336; font-weight: bold;")
    widget.timer_label.setStyleSheet("font-size: 64px; font-weight: bold; color: #eeeeee;")
    widget.vu_meter.setFixedSize(400, 20)
    widget.notes_input.setMinimumHeight(220)
    widget.pause_btn.setFixedSize(124, 50)
    widget.stop_btn.setFixedSize(124, 50)
    widget.cancel_btn.setFixedSize(124, 50)
    widget.workspace_split.setOrientation(Qt.Orientation.Horizontal)
