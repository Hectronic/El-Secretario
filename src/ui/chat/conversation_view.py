"""Scrollable conversation messages with answer-scoped actions and sources."""

from math import ceil

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


class AutoHeightTextBrowser(QTextBrowser):
    """Read-only rich text that grows to fit after width changes."""

    def setHtml(self, html):
        super().setHtml(html)
        QTimer.singleShot(0, self.adjust_to_document)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self.adjust_to_document)

    def adjust_to_document(self):
        width = max(1, self.viewport().width())
        self.document().setTextWidth(width)
        height = ceil(self.document().documentLayout().documentSize().height()) + 12
        self.setFixedHeight(max(38, height))


class ChatMessageCard(QFrame):
    """One message and the actions/evidence that belong to that message."""

    source_requested = pyqtSignal(int)

    def __init__(self, role, html, parent=None):
        super().__init__(parent)
        self.role = role
        self.setObjectName("chatMessageCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(5)

        self.content = AutoHeightTextBrowser(self)
        self.content.setReadOnly(True)
        self.content.setOpenExternalLinks(True)
        self.content.setFrameShape(QFrame.Shape.NoFrame)
        self.content.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.content.document().setDocumentMargin(2)
        self.content.setHtml(html)
        self.content.adjust_to_document()
        layout.addWidget(self.content)

        self.actions = QWidget(self)
        self.actions_layout = QHBoxLayout(self.actions)
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(5)
        self.actions.setVisible(False)
        layout.addWidget(self.actions)

        self.sources_toggle = QToolButton(self)
        self.sources_toggle.setCheckable(True)
        self.sources_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.sources_toggle.setArrowType(Qt.ArrowType.RightArrow)
        self.sources_toggle.setAccessibleName("Show answer sources")
        self.sources_toggle.toggled.connect(self._set_sources_expanded)
        self.sources_toggle.setVisible(False)
        layout.addWidget(self.sources_toggle, 0, Qt.AlignmentFlag.AlignLeft)

        self.sources_panel = QWidget(self)
        self.sources_layout = QVBoxLayout(self.sources_panel)
        self.sources_layout.setContentsMargins(10, 2, 2, 2)
        self.sources_layout.setSpacing(4)
        self.sources_panel.setVisible(False)
        layout.addWidget(self.sources_panel)

    def add_action(self, button):
        self.actions_layout.addWidget(button)
        self.actions.setVisible(True)

    def set_sources(self, sources, degraded=False):
        while self.sources_layout.count():
            item = self.sources_layout.takeAt(0)
            child = item.widget()
            if child:
                child.deleteLater()

        sources = list(sources or [])
        if not sources:
            message = (
                "La recuperación se degradó y no hay fuentes navegables."
                if degraded
                else "No hay información de procedencia para esta respuesta."
            )
            self.sources_toggle.setVisible(False)
            self.sources_panel.setVisible(True)
            status = QLabel(message, self.sources_panel)
            status.setWordWrap(True)
            status.setAccessibleName("Source availability status")
            self.sources_layout.addWidget(status)
            return

        self.sources_toggle.setVisible(True)
        self.sources_toggle.setChecked(False)
        self.sources_toggle.setText(f"Fuentes ({len(sources)})")
        self.sources_toggle.setToolTip("Mostrar las fuentes de esta respuesta")
        self.sources_toggle.setAccessibleName(f"Mostrar {len(sources)} fuentes de esta respuesta")
        self.sources_toggle.setProperty("expanded", False)
        for source in sources:
            row = QWidget(self.sources_panel)
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(2)
            try:
                record_id = int(source["source_id"])
            except (TypeError, ValueError):
                record_id = None
            title = QPushButton(f"{source['title']} · {source['role']}", row)
            title.setAccessibleName(f"Open source: {source['title']}")
            title.setProperty("class", "chat-source-link")
            title.setEnabled(record_id is not None)
            if record_id is not None:
                title.clicked.connect(
                    lambda _checked=False, rid=record_id: self.source_requested.emit(rid)
                )
            row_layout.addWidget(title)
            excerpt = QLabel(source.get("excerpt", ""), row)
            excerpt.setWordWrap(True)
            row_layout.addWidget(excerpt)
            if source.get("degraded"):
                degraded_label = QLabel("Recuperación mediante palabras clave.", row)
                row_layout.addWidget(degraded_label)
            self.sources_layout.addWidget(row)

        self.sources_panel.setVisible(False)

    def _set_sources_expanded(self, expanded):
        self.sources_panel.setVisible(bool(expanded))
        self.sources_toggle.setProperty("expanded", bool(expanded))
        self.sources_toggle.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
        )
        count = sum(
            1 for i in range(self.sources_layout.count())
            if self.sources_layout.itemAt(i).widget() is not None
        )
        state = "Ocultar" if expanded else "Mostrar"
        self.sources_toggle.setAccessibleName(f"{state} {count} fuentes de esta respuesta")
        self.sources_toggle.setToolTip(f"{state} las fuentes de esta respuesta")


class ConversationView(QWidget):
    """Conversation history that keeps each answer's evidence with it."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards = []
        self._display_bg = "transparent"
        self._display_text = "palette(text)"
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.messages_widget = QWidget(self.scroll_area)
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setContentsMargins(4, 4, 4, 4)
        self.messages_layout.setSpacing(4)
        self.messages_layout.addStretch(1)
        self.scroll_area.setWidget(self.messages_widget)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scroll_area)

    def add_message(self, role, html):
        card = ChatMessageCard(role, html, self.messages_widget)
        self._apply_card_theme(card)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, card)
        self._cards.append(card)
        self.scroll_to_bottom()
        return card

    def last_card(self, role=None):
        for card in reversed(self._cards):
            if role is None or card.role == role:
                return card
        return None

    def clear(self):
        while self._cards:
            card = self._cards.pop()
            self.messages_layout.removeWidget(card)
            card.deleteLater()

    def set_message_theme(self, display_bg, display_text):
        self._display_bg = display_bg
        self._display_text = display_text
        for card in self._cards:
            self._apply_card_theme(card)

    def _apply_card_theme(self, card):
        card.setStyleSheet(
            f"QFrame#chatMessageCard {{ background-color: {self._display_bg}; color: {self._display_text}; }}"
        )
        card.content.setStyleSheet(
            f"background-color: {self._display_bg}; color: {self._display_text}; border: none;"
        )
        card.content.document().setDefaultStyleSheet(
            f"body {{ color: {self._display_text}; }} a {{ color: #64b5f6; }}"
        )

    def toPlainText(self):
        return "\n".join(card.content.toPlainText() for card in self._cards)

    def toHtml(self):
        return "\n".join(card.content.toHtml() for card in self._cards)

    def verticalScrollBar(self):
        return self.scroll_area.verticalScrollBar()

    def scroll_to_bottom(self):
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
