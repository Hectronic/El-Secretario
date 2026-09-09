import hashlib

from PyQt6.QtCore import Qt, QStringListModel
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QCompleter, QLabel, QLineEdit


def _tag_palette(tag):
    digest = hashlib.md5((tag or "").strip().lower().encode("utf-8")).hexdigest()
    base = QColor.fromHsv(int(digest[:2], 16) % 360, 130, 215)
    return base.name(), base.darker(145).name(), "#111111" if base.lightness() > 145 else "#ffffff"


def create_tag_chip(tag, width=84, height=18, font_size=10, parent=None):
    bg, border, text_color = _tag_palette(tag)
    chip = QLabel(tag, parent); chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if width is None:
        chip.setFixedHeight(height); chip.setMinimumWidth(max(24, chip.fontMetrics().horizontalAdvance(tag) + 14))
    else:
        chip.setFixedSize(width, height)
    chip.setToolTip(tag)
    chip.setStyleSheet(f"QLabel {{background-color:{bg};color:{text_color};border:1px solid {border};border-radius:7px;padding:0px 4px;font-size:{font_size}px;font-weight:600;}}")
    return chip


class TagsLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent); self.setPlaceholderText("Etiquetas separadas por coma (ej: Trabajo, Reunión)")
        self.all_tags = []; self.completer_model = QStringListModel(); self.tags_completer = QCompleter()
        self.tags_completer.setModel(self.completer_model); self.tags_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.tags_completer.setFilterMode(Qt.MatchFlag.MatchContains); self.tags_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.tags_completer.activated.connect(self.insert_completion); self.setCompleter(self.tags_completer); self.textChanged.connect(self.update_completer_prefix)

    def set_tags(self, tags): self.all_tags = tags or []; self.completer_model.setStringList(self.all_tags)
    def get_current_tag_text(self): return self.text()[:self.cursorPosition()].rsplit(',', 1)[-1].strip()
    def update_completer_prefix(self):
        current = self.get_current_tag_text(); existing = [tag.strip().lower() for tag in self.text().split(',') if tag.strip()]
        self.completer_model.setStringList([tag for tag in self.all_tags if tag.lower() not in existing or tag.lower() == current.lower()])
        if current and self.tags_completer.completionCount() > 0: self.tags_completer.setCompletionPrefix(current); self.tags_completer.complete()
    def insert_completion(self, completion):
        before = self.text()[:self.cursorPosition()]; comma = before.rfind(','); prefix = "" if comma == -1 else self.text()[:comma + 1] + " "
        self.setText(prefix + completion + self.text()[self.cursorPosition():]); self.setCursorPosition(len(prefix) + len(completion))
