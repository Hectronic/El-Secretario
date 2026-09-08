"""Visual composition for CalendarWidget."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QListWidget, QPushButton, QSplitter, QTextEdit, QVBoxLayout, QWidget


def build_calendar_layout(widget):
    layout = QVBoxLayout(widget)
    
    # Main Splitter
    splitter = QSplitter(Qt.Orientation.Horizontal)
    
    # Left Panel: Actions & Tags (Simplified)
    left_widget = QWidget()
    left_layout = QVBoxLayout(left_widget)
    
    widget.selection_label = QLabel("<b>Selection Context:</b>\nNo context yet")
    widget.selection_label.setWordWrap(True)
    left_layout.addWidget(widget.selection_label)
    
    # Tag Filter (Keep it so users can refine the view within the tab)
    tag_group = QGroupBox("Filter by Tags")
    tag_layout = QVBoxLayout()
    widget.tag_list = QListWidget()
    widget.tag_list.itemChanged.connect(widget.on_tag_changed)
    tag_layout.addWidget(widget.tag_list)
    tag_group.setLayout(tag_layout)
    left_layout.addWidget(tag_group)
    
    # Action Buttons
    widget.summary_btn = QPushButton("Generate Weekly Summary")
    widget.summary_btn.clicked.connect(widget.on_generate_summary_clicked)
    left_layout.addWidget(widget.summary_btn)
    
    widget.daily_summary_btn = QPushButton("Generate Daily Summary")
    widget.daily_summary_btn.clicked.connect(widget.on_generate_daily_summary_clicked)
    left_layout.addWidget(widget.daily_summary_btn)
    
    widget.pending_btn = QPushButton("Generate All Pending")
    widget.pending_btn.clicked.connect(widget.on_generate_pending_clicked)
    left_layout.addWidget(widget.pending_btn)

    splitter.addWidget(left_widget)
    
    # Right Panel: Summaries & Recordings
    right_splitter = QSplitter(Qt.Orientation.Vertical)
    
    # Daily Summary
    daily_summary_widget = QWidget()
    daily_summary_layout = QVBoxLayout(daily_summary_widget)
    daily_summary_layout.setContentsMargins(0, 0, 0, 0)
    
    # Day Navigation Buttons
    header_layout = QHBoxLayout()
    widget.daily_summary_label = QLabel("<b>Daily Summary:</b>")
    header_layout.addWidget(widget.daily_summary_label)
    header_layout.addStretch()
    
    widget.prev_day_btn = QPushButton("<")
    widget.prev_day_btn.setFixedWidth(30)
    widget.prev_day_btn.clicked.connect(widget.navigate_prev_day)
    
    widget.today_btn = QPushButton("Today")
    widget.today_btn.clicked.connect(widget.navigate_today)
    
    widget.next_day_btn = QPushButton(">")
    widget.next_day_btn.setFixedWidth(30)
    widget.next_day_btn.clicked.connect(widget.navigate_next_day)
    
    header_layout.addWidget(widget.prev_day_btn)
    header_layout.addWidget(widget.today_btn)
    header_layout.addWidget(widget.next_day_btn)
    daily_summary_layout.addLayout(header_layout)
    
    widget.daily_summary_text = QTextEdit()
    widget.daily_summary_text.setReadOnly(True)
    daily_summary_layout.addWidget(widget.daily_summary_text)
    
    # Weekly Summary
    summary_widget = QWidget()
    summary_layout = QVBoxLayout(summary_widget)
    summary_layout.setContentsMargins(0, 0, 0, 0)
    summary_layout.addWidget(QLabel("<b>Weekly Summary:</b>"))
    widget.summary_text = QTextEdit()
    widget.summary_text.setReadOnly(True)
    summary_layout.addWidget(widget.summary_text)
    
    # Recordings List
    recordings_widget = QWidget()
    recordings_layout = QVBoxLayout(recordings_widget)
    recordings_layout.setContentsMargins(0, 0, 0, 0)
    recordings_layout.addWidget(QLabel("<b>Recordings:</b>"))
    widget.recording_list = QListWidget()
    recordings_layout.addWidget(widget.recording_list)
    
    widget.open_tab_btn = QPushButton("Start Chat with Selection")
    widget.open_tab_btn.clicked.connect(widget.request_new_chat_tab)
    widget.open_tab_btn.setMinimumHeight(40)
    recordings_layout.addWidget(widget.open_tab_btn)

    right_splitter.addWidget(summary_widget)
    right_splitter.addWidget(daily_summary_widget)
    right_splitter.addWidget(recordings_widget)
    
    splitter.addWidget(right_splitter)
    splitter.setSizes([250, 850])
    right_splitter.setSizes([300, 300, 400])
    
    layout.addWidget(splitter)
    
    widget.load_tags()

