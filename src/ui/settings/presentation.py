"""Compact, theme-aware presentation for the existing Settings controls."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QBoxLayout, QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel, QSizePolicy, QWidget


def compact_settings_panel(panel):
    panel.setProperty("settingsPanel", True)
    panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
    layout = panel.layout()
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(12)
    # The surface owns the single trailing stretch. Per-panel stretches used to
    # distribute spare window height between unrelated sections and RAG actions.
    for index in reversed(range(layout.count())):
        if layout.itemAt(index).spacerItem() is not None:
            layout.takeAt(index)
    for form in panel.findChildren(QFormLayout):
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
    for combo in panel.findChildren(QComboBox):
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(12)
    for label in panel.findChildren(QLabel):
        label.setWordWrap(True)
        style = label.styleSheet()
        if "font-size: 18px" in style or "font-size: 16px" in style:
            label.setStyleSheet("font-size: 16px; font-weight: 600; padding-top: 4px;")
            label.setWordWrap(True)
        elif "color: gray" in style or "color: #607D8B" in style:
            label.setStyleSheet("")
            label.setProperty("class", "settings-help")
            label.setWordWrap(True)


def settings_styles(dark):
    border = "#485361" if dark else "#d4dce6"
    muted = "#b5c1d0" if dark else "#526174"
    subtle = "#a2afbf" if dark else "#64748b"
    selected = "#254b6c" if dark else "#e1efff"
    hover = "#35404e" if dark else "#f0f5fb"
    text = "#f0f5fc" if dark else "#172b43"
    return f"""
        QListWidget#settingsCategories {{ border: 1px solid {border}; border-radius: 10px; padding: 6px; }}
        QListWidget#settingsCategories::item {{ padding: 10px 12px; border: none; border-radius: 6px; min-height: 20px; }}
        QListWidget#settingsCategories::item:selected {{ background: {selected}; color: {text}; font-weight: 600; }}
        QListWidget#settingsCategories::item:hover {{ background: {hover}; }}
        QWidget[settingsPanel="true"] {{ border: 1px solid {border}; border-radius: 10px; }}
        QLabel#settingsCategoryHeading {{ font-size: 20px; font-weight: 600; padding: 2px 0; }}
        QLabel#settingsCategorySummary, QLabel[class="settings-help"] {{ color: {muted}; font-size: 12px; }}
        QLabel[class="settings-default"] {{ color: {subtle}; font-size: 11px; }}
        QLabel#advancedSettingsSummary {{ color: {muted}; background: {hover}; border-radius: 6px; padding: 8px 10px; font-size: 12px; }}
        QPushButton {{ min-height: 22px; padding: 5px 12px; }}
        QPushButton#settingsSaveButton {{ background: #2168a6; color: white; border: 1px solid #408ac8; border-radius: 6px; font-weight: 600; }}
        QPushButton#settingsSaveButton:disabled {{ background: {hover}; color: {subtle}; border-color: {border}; }}
        QLineEdit#settingsSearch {{ min-height: 24px; }}
    """


def collapse_hidden_form_rows(panel):
    for form in panel.findChildren(QFormLayout):
        for row in range(form.rowCount()):
            widgets = [form.itemAt(row, role) for role in (
                QFormLayout.ItemRole.LabelRole, QFormLayout.ItemRole.FieldRole,
                QFormLayout.ItemRole.SpanningRole,
            )]
            visible = any(item is not None and item.widget() is not None
                          and not item.widget().isHidden() for item in widgets)
            form.setRowVisible(row, visible)


class CheckBoxDescription(QLabel):
    """A wrapping checkbox caption that preserves click-to-toggle behavior."""

    def __init__(self, checkbox, category):
        super().__init__(checkbox.text())
        self.checkbox = checkbox
        self.setProperty("settingsCategory", category)
        self.setWordWrap(True)
        self.setBuddy(checkbox)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.checkbox.isEnabled():
            self.checkbox.click()
            event.accept()
        else:
            super().mouseReleaseEvent(event)


def setting_control_view(control, category):
    if not isinstance(control, QCheckBox) or not control.text():
        return control
    # Native QCheckBox captions cannot wrap and impose the full sentence as a
    # minimum width, especially with Windows fonts and display scaling.
    caption = CheckBoxDescription(control, category)
    if not control.accessibleName():
        control.setAccessibleName(control.text())
    control.setText("")
    row = QWidget(control.parentWidget())
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    layout.addWidget(control, 0, Qt.AlignmentFlag.AlignTop)
    layout.addWidget(caption, 1)
    return row


def set_compact_settings_panel(panel, compact):
    policy = (QFormLayout.RowWrapPolicy.WrapAllRows if compact
              else QFormLayout.RowWrapPolicy.WrapLongRows)
    for form in panel.findChildren(QFormLayout):
        form.setRowWrapPolicy(policy)
    direction = (QBoxLayout.Direction.TopToBottom if compact
                 else QBoxLayout.Direction.LeftToRight)
    for name in ("settingsFieldActions", "settingsSectionActions"):
        for row in panel.findChildren(QBoxLayout, name):
            row.setDirection(direction)
