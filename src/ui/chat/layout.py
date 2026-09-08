"""Visual composition and theme application for ChatWidget."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QCursor
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QLabel, QPushButton, QSplitter, QTextEdit, QToolButton, QVBoxLayout, QWidget

from src.ui.context_manager_panel import ContextManagerPanel
from src.ui.chat.theme_styles import build_chat_widget_theme


def build_chat_layout(widget):
    root_layout = QVBoxLayout(widget)
    root_layout.setContentsMargins(0, 0, 0, 0)
    root_layout.setSpacing(0)

    widget.header = QFrame()
    widget.header.setObjectName("chatWidgetHeader")
    widget.header.setFixedHeight(32)
    header_layout = QHBoxLayout(widget.header)
    header_layout.setContentsMargins(8, 3, 6, 3)
    header_layout.setSpacing(4)

    widget.title_label = QLabel("New Chat")
    header_layout.addWidget(widget.title_label, 1)
    widget.header.installEventFilter(widget)
    widget.title_label.installEventFilter(widget)

    widget.mode_btn = QToolButton()
    widget.mode_btn.setAutoRaise(True)
    widget.mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.mode_btn.setFixedSize(20, 20)
    widget.mode_btn.clicked.connect(widget._toggle_display_mode)
    header_layout.addWidget(widget.mode_btn)

    widget.minimize_btn = QToolButton()
    widget.minimize_btn.setText("_")
    widget.minimize_btn.setToolTip("Minimize to compact chip")
    widget.minimize_btn.setAutoRaise(True)
    widget.minimize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.minimize_btn.setFixedSize(20, 20)
    widget.minimize_btn.clicked.connect(widget._toggle_minimized_state)
    header_layout.addWidget(widget.minimize_btn)

    widget.close_btn = QToolButton()
    widget.close_btn.setText("×")
    widget.close_btn.setToolTip("Close chat")
    widget.close_btn.setAutoRaise(True)
    widget.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.close_btn.setFixedSize(20, 20)
    widget.close_btn.clicked.connect(lambda: widget.close_requested.emit(widget))
    header_layout.addWidget(widget.close_btn)

    root_layout.addWidget(widget.header)

    widget.content_container = QWidget()
    main_layout = QHBoxLayout(widget.content_container)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)
    
    widget.splitter = QSplitter(Qt.Orientation.Horizontal)
    
    # --- Left Side: Chat ---
    chat_container = QWidget()
    chat_layout = QVBoxLayout(chat_container)

    # Chat Display
    widget.display = QTextEdit()
    widget.display.setReadOnly(True)
    widget.display.setPlaceholderText("Pregunta cualquier cosa sobre tus notas...")
    chat_layout.addWidget(widget.display)

    # Input Area
    input_layout = QHBoxLayout()
    widget.input_field = QLineEdit()
    widget.input_field.setPlaceholderText("Escribe tu pregunta aquí...")
    widget.input_field.returnPressed.connect(widget.send_message)
    input_layout.addWidget(widget.input_field)

    widget.send_btn = QPushButton("Enviar")
    widget.send_btn.clicked.connect(widget.send_message)
    widget.send_btn.setProperty("class", "calendar-primary-btn")
    widget.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.send_btn.setFixedHeight(36)
    input_layout.addWidget(widget.send_btn)

    chat_layout.addLayout(input_layout)
    
    widget.splitter.addWidget(chat_container)
    
    # --- Right Side: Context Manager Panel ---
    widget.context_panel = ContextManagerPanel(widget.db, widget.notebook_db, widget)
    widget.context_panel.toggle_requested.connect(widget.toggle_context_panel)
    widget.context_panel.add_context_requested.connect(widget.add_context)
    widget.context_panel.reset_extra_context_requested.connect(widget.reset_extra_context)
    widget.context_panel.clear_chat_requested.connect(widget.clear_history)
    widget.splitter.addWidget(widget.context_panel)
    widget.splitter.splitterMoved.connect(widget._remember_context_panel_sizes)
    
    widget.splitter.setSizes([900, 350])
    main_layout.addWidget(widget.splitter)
    root_layout.addWidget(widget.content_container)
    widget._apply_theme_styles()
    widget.set_display_mode("tab")
    widget._refresh_title()



def apply_chat_theme(widget):
    theme = build_chat_widget_theme(widget._is_dark_theme())
    header_bg = theme["header_bg"]
    header_border = theme["header_border"]
    title_color = theme["title_color"]
    btn_color = theme["btn_color"]
    btn_hover = theme["btn_hover"]
    display_bg = theme["display_bg"]
    display_text = theme["display_text"]
    input_bg = theme["input_bg"]
    input_border = theme["input_border"]
    display_border = theme["display_border"]

    widget.header.setStyleSheet(f"""
        QFrame#chatWidgetHeader {{
            background-color: {header_bg};
            border-bottom: 1px solid {header_border};
            border-top-left-radius: 11px;
            border-top-right-radius: 11px;
        }}
    """)
    widget.title_label.setStyleSheet(
        f"font-weight: 600; font-size: 12px; color: {title_color};"
    )

    action_btn_style = f"""
        QToolButton {{
            border: none;
            border-radius: 6px;
            padding: 1px;
            background: transparent;
            color: {btn_color};
            font-size: 11px;
            font-weight: 700;
        }}
        QToolButton:hover {{
            background-color: {btn_hover};
            color: #2196F3;
        }}
    """
    widget.mode_btn.setStyleSheet(action_btn_style)
    widget.minimize_btn.setStyleSheet(action_btn_style)
    widget.close_btn.setStyleSheet(
        action_btn_style
        + """
        QToolButton:hover {
            background-color: rgba(244, 67, 54, 0.15);
            color: #f44336;
        }
        """
    )
    widget.display.setStyleSheet(f"""
        QTextEdit {{
            background-color: {display_bg};
            color: {display_text};
            border: 1px solid {display_border};
            border-radius: 8px;
            font-size: 14px;
            padding: 10px;
            line-height: 1.5;
        }}
    """)
    widget.display.document().setDefaultStyleSheet(
        f"body {{ color: {display_text}; }} a {{ color: #64b5f6; }}"
    )
    widget.input_field.setStyleSheet(f"""
        QLineEdit {{
            background-color: {input_bg};
            color: {display_text};
            border: 1px solid {input_border};
            border-radius: 18px;
            padding: 8px 15px;
            font-size: 13px;
        }}
    """)

