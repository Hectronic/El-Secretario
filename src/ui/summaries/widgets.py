"""Small reusable Qt widgets used inside summary views."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QTextBrowser, QVBoxLayout, QWidget

from src.ui.component_widgets.tags import create_tag_chip


class AutoSizingMarkdownView(QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True); self.setOpenExternalLinks(True); self.setFrameShape(QFrame.Shape.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizeAdjustPolicy(QTextBrowser.SizeAdjustPolicy.AdjustToContents)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.document().documentLayout().documentSizeChanged.connect(self._update_height)
        self._update_height()

    def setMarkdown(self, markdown):
        super().setMarkdown(markdown); self._update_height()

    def _update_height(self, *_args):
        margins = self.contentsMargins()
        height = max(140, int(self.document().size().height()) + margins.top() + margins.bottom() + self.frameWidth() * 2 + 18)
        self.setMinimumHeight(height); self.setMaximumHeight(height)


class WeeklyRecordingRowWidget(QWidget):
    open_requested = pyqtSignal(int)

    def __init__(self, record, parent=None):
        super().__init__(parent); self.record = record or {}; self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self); layout.setContentsMargins(12, 12, 12, 12); layout.setSpacing(12)
        text_col = QVBoxLayout(); text_col.setSpacing(5)
        title = QLabel((self.record.get("title") or "Untitled recording").strip()); title.setStyleSheet("font-size: 14px; font-weight: 700;"); text_col.addWidget(title)
        created_at = str(self.record.get("created_at") or "").strip(); duration = float(self.record.get("duration") or 0)
        meta_bits = [created_at[:16]] if created_at else []
        if duration > 0: meta_bits.append(f"{duration:.1f}s")
        if self.record.get("summary"): meta_bits.append("Summary ready")
        if self.record.get("is_favorite"): meta_bits.append("Favorite")
        meta = QLabel(" • ".join(meta_bits)); meta.setStyleSheet("font-size: 11px; color: palette(mid);"); text_col.addWidget(meta)
        chips = QHBoxLayout(); chips.setSpacing(4)
        tags = [tag.strip() for tag in str(self.record.get("tags") or "").split(",") if tag.strip()]
        if tags:
            for tag in tags[:4]: chips.addWidget(create_tag_chip(tag, width=None, height=18, font_size=9, parent=self))
        else:
            empty = QLabel("No tags"); empty.setStyleSheet("font-size: 10px; color: palette(mid);"); chips.addWidget(empty)
        chips.addStretch(); text_col.addLayout(chips); layout.addLayout(text_col, 1)
        button = QPushButton("Open"); button.setProperty("class", "calendar-nav-btn"); button.setCursor(Qt.CursorShape.PointingHandCursor); button.setMinimumHeight(32); button.clicked.connect(self._emit_open); layout.addWidget(button, 0, Qt.AlignmentFlag.AlignVCenter)
        self.setStyleSheet("background-color: palette(base);border: 1px solid palette(midlight);border-radius: 14px;")

    def _emit_open(self):
        record_id = self.record.get("id")
        if isinstance(record_id, int): self.open_requested.emit(record_id)
