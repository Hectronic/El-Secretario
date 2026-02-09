
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QLabel, 
                             QHBoxLayout, QPushButton, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal

class SummaryViewerWidget(QWidget):
    """
    Widget to display a daily or weekly summary in a read-only view.
    """
    close_requested = pyqtSignal()
    regenerate_requested = pyqtSignal(dict)
    
    def __init__(self, summary_data, parent=None):
        super().__init__(parent)
        self.summary_data = summary_data
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        
        type_ = self.summary_data.get('type', 'daily')
        if type_ == 'daily':
            title_text = f"📅 Daily Summary - {self.summary_data.get('date')}"
        else:
            title_text = f"Week Summary - Week of {self.summary_data.get('week_start')}"
            
        title = QLabel(title_text)
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2196F3;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Close button (optional, as tabs have close buttons, but good for UX)
        # self.close_btn = QPushButton("Close")
        # self.close_btn.clicked.connect(self.close_requested.emit)
        # header_layout.addWidget(self.close_btn)
        
        layout.addLayout(header_layout)
        
        # Metadata / Info
        meta_layout = QHBoxLayout()
        generated_at = self.summary_data.get('generated_at', 'Unknown')
        generated_at = self.summary_data.get('generated_at', 'Unknown')
        self.meta_label = QLabel(f"Generated at: {generated_at}")
        self.meta_label.setStyleSheet("color: #777; font-size: 12px;")
        meta_layout.addWidget(self.meta_label)
        
        meta_layout.addStretch()
        layout.addLayout(meta_layout)
        
        # Content
        self.content_area = QTextEdit()
        self.content_area.setReadOnly(True)
        self.content_area.setMarkdown(self.summary_data.get('summary', ''))
        self.content_area.setStyleSheet("font-size: 14px; line-height: 1.6;")
        layout.addWidget(self.content_area)
        
        
        # Actions bar (for future: Regenerate, Export, etc.)
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()

        if self.summary_data.get('type') == 'daily':
            copy_btn = QPushButton("Copy to Clipboard") # Placeholder or implement
            # actions_layout.addWidget(copy_btn)
            
            regenerate_btn = QPushButton("↻ Regenerate")
            regenerate_btn.setToolTip("Regenerate this daily summary (will check for new recordings)")
            regenerate_btn.clicked.connect(lambda: self.regenerate_requested.emit(self.summary_data))
            actions_layout.addWidget(regenerate_btn)
            
        layout.addLayout(actions_layout)

    def update_content(self, summary_data):
        """Update the content of the viewer with new data."""
        self.summary_data = summary_data
        self.content_area.setMarkdown(self.summary_data.get('summary', ''))
        
        generated_at = self.summary_data.get('generated_at', 'Unknown')
        self.meta_label.setText(f"Generated at: {generated_at}")
