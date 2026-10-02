"""Presentation policy for tabbed, floating, and minimized chat modes."""

from PyQt6.QtCore import Qt

from src.ui.chat.header_state import build_chat_header_state


def apply_context_panel_visibility(widget):
    visible = (
        widget.display_mode == "floating"
        and not widget.floating_minimized
        and widget.floating_context_editor_open
    )
    widget.context_panel.setVisible(visible)
    if not visible:
        widget.context_panel.setMinimumWidth(0)
        widget.context_panel.setMaximumWidth(16777215)
        widget.splitter.setSizes([max(1, widget.width()), 0])
        return
    widget.context_panel.setMinimumWidth(280); widget.context_panel.setMaximumWidth(16777215)
    widget.splitter.setSizes([max(1, widget.width() - 300), 300])


def apply_display_mode(widget, mode):
    widget.display_mode = "floating" if mode == "floating" else "tab"
    if widget.display_mode != "floating" or widget.floating_minimized:
        widget.floating_context_editor_open = False
    state = build_chat_header_state(widget.display_mode, widget.floating_minimized)
    widget.layout().setContentsMargins(*([state["layout_margin"]] * 4))
    widget.header.setVisible(state["header_visible"])
    widget.mode_btn.setText(state["mode_btn_text"]); widget.mode_btn.setToolTip(state["mode_btn_tooltip"])
    widget.minimize_btn.setVisible(state["minimize_visible"]); widget.content_container.setVisible(state["content_visible"])
    widget.minimize_btn.setText(state["minimize_btn_text"]); widget.minimize_btn.setToolTip(state["minimize_btn_tooltip"])
    widget.header.setCursor(Qt.CursorShape.PointingHandCursor if state["cursor"] == "pointing" else Qt.CursorShape.ArrowCursor)
    widget.title_label.setCursor(widget.header.cursor())
    apply_context_panel_visibility(widget)
    if widget.display_mode == "floating":
        widget.splitter.setSizes([740, 0])
    else:
        widget.splitter.setSizes([max(1, widget.width()), 0])
