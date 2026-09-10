"""Qt composition for the reusable chat-context panel."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QGroupBox, QHBoxLayout, QLabel, QListWidget, QPushButton, QToolButton, QVBoxLayout, QWidget


def build_context_panel_view(panel):
    layout = QVBoxLayout(panel); layout.setContentsMargins(10, 10, 10, 10); layout.setSpacing(12)
    panel.header = QWidget(); header = QHBoxLayout(panel.header); header.setContentsMargins(0, 0, 0, 0)
    panel.header_label = QLabel("Chat Context"); panel.header_label.setStyleSheet("font-size: 14px; font-weight: 700;"); header.addWidget(panel.header_label, 1)
    panel.toggle_btn = QToolButton(); panel.toggle_btn.setAutoRaise(True); panel.toggle_btn.setFixedSize(24, 24); panel.toggle_btn.setText("⟩"); panel.toggle_btn.setToolTip("Collapse context panel"); panel.toggle_btn.clicked.connect(panel.toggle_requested.emit); header.addWidget(panel.toggle_btn); layout.addWidget(panel.header)
    panel.content_widget = QWidget(); content = QVBoxLayout(panel.content_widget); content.setContentsMargins(0, 0, 0, 0); content.setSpacing(12)
    entries = QGroupBox("Detected Context Entries"); entries_layout = QVBoxLayout(entries); panel.entries_list = QListWidget(); entries_layout.addWidget(panel.entries_list); panel.entries_count_lbl = QLabel("0 entries found"); entries_layout.addWidget(panel.entries_count_lbl); content.addWidget(entries)
    status = QGroupBox("Selection Context"); status_layout = QVBoxLayout(status); panel.sync_cb = QCheckBox("Sync with App"); panel.sync_cb.setChecked(True); status_layout.addWidget(panel.sync_cb); panel.date_lbl = QLabel("Dates: all history"); panel.date_lbl.setWordWrap(True); status_layout.addWidget(panel.date_lbl); panel.tags_lbl = QLabel("Tags: all"); panel.tags_lbl.setWordWrap(True); status_layout.addWidget(panel.tags_lbl); content.addWidget(status)
    notebooks = QGroupBox("Include Notebooks"); notebooks_layout = QVBoxLayout(notebooks); panel.nb_list = QListWidget(); panel.nb_list.setFixedHeight(120); panel.nb_list.itemChanged.connect(panel.on_metadata_changed); notebooks_layout.addWidget(panel.nb_list); content.addWidget(notebooks)
    for attr, text, signal in (("add_context_btn", "Add Context", panel.add_context_requested), ("reset_context_btn", "Reset Extra Context", panel.reset_extra_context_requested), ("clear_chat_btn", "Clear Chat History", panel.clear_chat_requested)):
        button = QPushButton(text); button.clicked.connect(signal.emit); setattr(panel, attr, button); content.addWidget(button)
    layout.addWidget(panel.content_widget); layout.addStretch(); panel.set_interactive(panel._interactive); panel.header.setVisible(panel._show_header); panel.toggle_btn.setVisible(panel._show_header)
