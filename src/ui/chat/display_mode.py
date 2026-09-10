"""Presentation policy for tabbed, floating, and minimized chat modes."""

from PyQt6.QtCore import Qt

from src.ui.chat.header_state import build_chat_header_state


def apply_context_panel_visibility(widget):
    visible = widget.display_mode != "floating" and not widget.floating_minimized
    widget.context_panel.setVisible(visible)
    if not visible:
        widget.context_panel.setMinimumWidth(0); widget.context_panel.setMaximumWidth(16777215); return
    widget.context_panel.set_collapsed(widget.context_panel_collapsed)
    if widget.context_panel_collapsed:
        width = widget.context_panel.COLLAPSED_WIDTH
        widget.context_panel.setMinimumWidth(width); widget.context_panel.setMaximumWidth(width)
        widget.splitter.setSizes([max(1, widget.width() - width), width]); return
    widget.context_panel.setMinimumWidth(280); widget.context_panel.setMaximumWidth(16777215)
    widget.splitter.setSizes(widget._context_panel_saved_sizes if len(widget._context_panel_saved_sizes) == 2 else [900, 350])


def apply_display_mode(widget, mode):
    widget.display_mode = "floating" if mode == "floating" else "tab"
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
    elif widget.context_panel_collapsed:
        width = widget.context_panel.COLLAPSED_WIDTH
        widget.splitter.setSizes([max(1, widget.width() - width), width])
