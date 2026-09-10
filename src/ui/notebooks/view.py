"""Qt composition for the notebook shell."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QProgressBar, QPushButton, QVBoxLayout

from src.ui.styles import LIST_WIDGET_STYLE


def build_notebook_view(widget):
    layout = QVBoxLayout(widget); header = QHBoxLayout()
    title = QLabel(f"Notebook: {widget.notebook_name}"); title.setStyleSheet("font-size: 20px; font-weight: bold;"); header.addWidget(title); header.addStretch()
    add = QPushButton("📝 Add Note"); add.clicked.connect(widget.add_text_note); header.addWidget(add)
    widget.record_btn = QPushButton("🎤 Record Voice Note"); widget.record_btn.clicked.connect(widget.toggle_recording); widget.record_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 5px 10px; border-radius: 5px; }"); header.addWidget(widget.record_btn)
    chat = QPushButton("💬 Chat"); chat.clicked.connect(lambda: widget.chat_requested.emit(widget.notebook_id, widget.notebook_name)); header.addWidget(chat); layout.addLayout(header)
    status = QHBoxLayout(); status.setAlignment(Qt.AlignmentFlag.AlignCenter)
    widget.rec_indicator = QLabel(); widget.rec_indicator.setFixedSize(16, 16); widget.rec_indicator.setStyleSheet("background-color: red; border-radius: 8px;"); widget.rec_indicator.hide(); status.addWidget(widget.rec_indicator)
    widget.rec_status = QLabel("Recording: 00:00"); widget.rec_status.setStyleSheet("color: #f44336; font-weight: bold; font-size: 14px;"); widget.rec_status.hide(); status.addWidget(widget.rec_status)
    widget.vu_meter = QProgressBar(); widget.vu_meter.setRange(0, 100); widget.vu_meter.setTextVisible(False); widget.vu_meter.setFixedSize(150, 10); widget.vu_meter.hide(); status.addWidget(widget.vu_meter); layout.addLayout(status)
    widget.entries_list = QListWidget(); widget.entries_list.setStyleSheet(LIST_WIDGET_STYLE); widget.entries_list.itemDoubleClicked.connect(widget.on_item_double_clicked); widget.entries_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); widget.entries_list.customContextMenuRequested.connect(widget.show_context_menu); layout.addWidget(widget.entries_list)
