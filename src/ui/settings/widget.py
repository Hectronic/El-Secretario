# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.

"""Searchable, staged Settings shell around the compatible feature panels."""

import json
import os

from PyQt6.QtCore import QSettings, QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QBoxLayout,
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.ui.settings.audio_panel import AudioSettingsPanel
from src.ui.settings.catalog import (
    CATEGORIES,
    CATEGORY_SUMMARIES,
    SettingDescriptor,
    build_setting_catalog,
    effective_defaults,
)
from src.ui.settings.general_panel import GeneralSettingsPanel
from src.ui.settings.prompts_panel import PromptsSettingsPanel
from src.ui.settings.productivity_panel import ProductivitySettingsPanel
from src.ui.settings.rag_panel import RAGSettingsPanel
from src.ui.settings.store import SettingsOverlay


RESTART_KEYS = {"enable_auto_update", "enable_mcp_server"}


class SettingsWidget(QWidget):
    rag_initialize_requested = pyqtSignal(dict)
    rag_reload_requested = pyqtSignal(dict)
    rag_reindex_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("Hectronic", "Secretario")
        self.overlay = SettingsOverlay(self.settings)
        self._category = self.settings.value("settings/category", CATEGORIES[0])
        if self._category not in CATEGORIES:
            self._category = CATEGORIES[0]
        self._advanced = self.settings.value("settings/advanced_mode", False, type=bool)
        self._previous_search_category = self._category
        self._search_override = None
        self._restoring_category = False
        self._leave_decision = None
        self._apply_retry_keys = set()
        self._pending_restart_keys, self._pending_restart_values = self._load_pending_restart()
        self._build_shell()
        self._build_panels()
        self._stage_all()
        self._baseline_values = dict(self.overlay._values)
        self._show_category(self._category)
        self._set_advanced(self._advanced, persist=False)
        self._refresh_dirty_state()
        self._refresh_restart_status()

    @property
    def tab_widget(self):
        """Compatibility alias retained for callers that inspect old Settings tabs."""
        return self.category_list

    def _build_shell(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 12)
        root.setSpacing(10)

        title_row = QHBoxLayout()
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        title_row.addWidget(title)
        title_row.addStretch(1)
        self.advanced_toggle = QCheckBox("Advanced settings")
        self.advanced_toggle.setAccessibleName("Show advanced settings")
        self.advanced_toggle.setChecked(self._advanced)
        self.advanced_toggle.toggled.connect(self._set_advanced)
        title_row.addWidget(self.advanced_toggle)
        root.addLayout(title_row)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("settingsSearch")
        self.search_input.setPlaceholderText("Search settings (for example microphone, GPU, idioma)…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setAccessibleName("Search settings")
        self.search_input.textChanged.connect(self._update_search_results)
        root.addWidget(self.search_input)

        body = QHBoxLayout()
        body.setSpacing(12)
        self.category_list = QListWidget()
        self.category_list.setObjectName("settingsCategories")
        self.category_list.setMinimumWidth(205)
        self.category_list.setMaximumWidth(270)
        for category in CATEGORIES:
            item = QListWidgetItem(category)
            item.setToolTip(CATEGORY_SUMMARIES[category])
            self.category_list.addItem(item)
        self.category_list.currentRowChanged.connect(self._on_category_changed)
        body.addWidget(self.category_list)

        content = QVBoxLayout()
        content.setSpacing(8)
        self.category_summary = QLabel()
        self.category_summary.setWordWrap(True)
        content.addWidget(self.category_summary)
        self.advanced_summary = QLabel()
        self.advanced_summary.setWordWrap(True)
        self.advanced_summary.setObjectName("advancedSettingsSummary")
        content.addWidget(self.advanced_summary)

        self.search_results = QListWidget()
        self.search_results.setObjectName("settingsSearchResults")
        self.search_results.itemClicked.connect(self._open_search_result)
        self.search_results.hide()
        content.addWidget(self.search_results)

        self.surface_scroll = QScrollArea()
        self.surface_scroll.setWidgetResizable(True)
        self.surface_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.surface_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.surface = QWidget()
        self.surface.setObjectName("settingsControls")
        self.surface_layout = QVBoxLayout(self.surface)
        self.surface_layout.setContentsMargins(0, 0, 10, 0)
        self.surface_layout.setSpacing(12)
        self.surface_scroll.setWidget(self.surface)
        content.addWidget(self.surface_scroll, 1)
        body.addLayout(content, 1)
        root.addLayout(body, 1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("settingsSaveStatus")
        self.status_label.setWordWrap(True)
        status_row = QHBoxLayout()
        status_row.addWidget(self.status_label, 1)
        self.apply_retry_btn = QPushButton("Retry apply")
        self.apply_retry_btn.setAccessibleName("Retry applying saved settings")
        self.apply_retry_btn.clicked.connect(self._retry_runtime_apply)
        self.apply_retry_btn.hide()
        status_row.addWidget(self.apply_retry_btn)
        root.addLayout(status_row)

        self.restart_status_label = QLabel("")
        self.restart_status_label.setObjectName("settingsRestartStatus")
        self.restart_status_label.setWordWrap(True)
        self.restart_btn = QPushButton("Restart application")
        self.restart_btn.clicked.connect(self._request_restart)
        restart_row = QHBoxLayout()
        restart_row.addWidget(self.restart_status_label, 1)
        restart_row.addWidget(self.restart_btn)
        root.addLayout(restart_row)

        footer = QHBoxLayout()
        self.reset_category_btn = QPushButton("Reset category…")
        self.reset_category_btn.clicked.connect(self._reset_category)
        footer.addWidget(self.reset_category_btn)
        footer.addStretch(1)
        self.discard_btn = QPushButton("Discard changes")
        self.discard_btn.clicked.connect(self.discard_settings)
        footer.addWidget(self.discard_btn)
        self.save_btn = QPushButton("Save settings")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self.save_settings)
        footer.addWidget(self.save_btn)
        root.addLayout(footer)

    def _build_panels(self):
        self._clear_surface()
        self.general_panel = GeneralSettingsPanel(self.overlay, self, auto_fetch_ollama=False)
        self.audio_panel = AudioSettingsPanel(self.overlay, self)
        self.rag_panel = RAGSettingsPanel(self.overlay, self)
        self.prompts_panel = PromptsSettingsPanel(self.overlay, self)
        self.productivity_panel = ProductivitySettingsPanel(self.overlay, self)
        for panel in (
            self.general_panel, self.audio_panel, self.rag_panel,
            self.prompts_panel, self.productivity_panel,
        ):
            self.surface_layout.addWidget(panel)

        self.rag_actions_widget = QWidget(self.surface)
        action_layout = QHBoxLayout(self.rag_actions_widget)
        action_layout.setContentsMargins(0, 8, 0, 8)
        self.rag_init_btn = QPushButton("Initialize RAG")
        self.rag_reload_btn = QPushButton("Reload RAG")
        self.rag_reindex_btn = QPushButton("Queue RAG reindex")
        self.rag_init_btn.clicked.connect(self._initialize_rag)
        self.rag_reload_btn.clicked.connect(self._reload_rag)
        self.rag_reindex_btn.clicked.connect(self._queue_rag_reindex)
        action_layout.addWidget(self.rag_init_btn)
        action_layout.addWidget(self.rag_reload_btn)
        action_layout.addWidget(self.rag_reindex_btn)
        action_layout.addStretch(1)
        self.surface_layout.addWidget(self.rag_actions_widget)

        self.catalog = build_setting_catalog(self)
        self.defaults = effective_defaults(self.catalog)
        for field in self.catalog:
            self._install_field_chrome(field)
        self._prepare_static_controls()
        self._connect_dirty_tracking()

    def _connect_dirty_tracking(self):
        seen = set()
        for field in self.catalog:
            control = field.control
            if id(control) in seen:
                continue
            seen.add(id(control))
            for signal_name in ("textChanged", "currentTextChanged", "toggled", "valueChanged"):
                signal = getattr(control, signal_name, None)
                if signal is not None:
                    signal.connect(self._schedule_dirty_refresh)

    def _schedule_dirty_refresh(self, *_args):
        QTimer.singleShot(0, self._on_control_changed)

    def _on_control_changed(self):
        self._refresh_dirty_state()
        self._update_advanced_summary()

    def _clear_surface(self):
        while self.surface_layout.count():
            item = self.surface_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _install_field_chrome(self, field: SettingDescriptor):
        target = field.view
        layout_info = self._find_layout_item(self.surface_layout, target)
        if layout_info is None:
            return
        layout, index = layout_info
        if isinstance(layout, QFormLayout):
            row, role = layout.getWidgetPosition(target)
            label_item = layout.itemAt(row, QFormLayout.ItemRole.LabelRole)
            field.row_label = label_item.widget() if label_item else None
            wrapper = QWidget(target.parentWidget())
            wrapper.setProperty("settingsCategory", field.category)
            wrapper.setProperty("settingsAdvanced", field.advanced)
            wrap_layout = QVBoxLayout(wrapper)
            wrap_layout.setContentsMargins(0, 2, 0, 4)
            wrap_layout.setSpacing(3)
            control_row = QHBoxLayout()
            control_row.setContentsMargins(0, 0, 0, 0)
            target.setParent(wrapper)
            control_row.addWidget(target, 1)
            reset = QPushButton("Reset")
            reset.setAccessibleName(f"Reset {field.label} to default")
            reset.setToolTip(f"Restore default: {self._default_text(field)}")
            reset.setObjectName("resetSetting_" + field.key.replace("/", "_"))
            reset.clicked.connect(field.reset)
            control_row.addWidget(reset)
            wrap_layout.addLayout(control_row)
            help_label = QLabel(field.help + "  " + field.timing, wrapper)
            help_label.setWordWrap(True)
            help_label.setProperty("class", "settings-help")
            wrap_layout.addWidget(help_label)
            default_label = QLabel("Default: " + self._default_text(field), wrapper)
            default_label.setWordWrap(True)
            default_label.setProperty("class", "settings-default")
            wrap_layout.addWidget(default_label)
            field.error_label = QLabel("", wrapper)
            field.error_label.setWordWrap(True)
            field.error_label.setAccessibleName(f"{field.label} validation message")
            field.error_label.setStyleSheet("color: #b3261e; font-weight: bold;")
            field.error_label.hide()
            wrap_layout.addWidget(field.error_label)
            layout.setWidget(row, role, wrapper)
            field.wrapper = wrapper
            if field.row_label:
                field.row_label.setProperty("settingsCategory", field.category)
                field.row_label.setProperty("settingsAdvanced", field.advanced)
                field.row_label.setWordWrap(True)
        elif isinstance(layout, QBoxLayout):
            wrapper = QWidget(target.parentWidget())
            wrapper.setProperty("settingsCategory", field.category)
            wrapper.setProperty("settingsAdvanced", field.advanced)
            wrap_layout = QVBoxLayout(wrapper)
            wrap_layout.setContentsMargins(0, 4, 0, 4)
            control_row = QHBoxLayout()
            target.setParent(wrapper)
            control_row.addWidget(target, 1)
            reset = QPushButton("Reset")
            reset.setAccessibleName(f"Reset {field.label} to default")
            reset.setToolTip(f"Restore default: {self._default_text(field)}")
            reset.setObjectName("resetSetting_" + field.key.replace("/", "_"))
            reset.clicked.connect(field.reset)
            control_row.addWidget(reset)
            wrap_layout.addLayout(control_row)
            help_label = QLabel(field.help + "  " + field.timing, wrapper)
            help_label.setWordWrap(True)
            wrap_layout.addWidget(help_label)
            default_label = QLabel("Default: " + self._default_text(field), wrapper)
            default_label.setWordWrap(True)
            wrap_layout.addWidget(default_label)
            field.error_label = QLabel("", wrapper)
            field.error_label.setWordWrap(True)
            field.error_label.setAccessibleName(f"{field.label} validation message")
            field.error_label.setStyleSheet("color: #b3261e; font-weight: bold;")
            field.error_label.hide()
            wrap_layout.addWidget(field.error_label)
            layout.removeWidget(target)
            layout.insertWidget(index, wrapper)
            field.wrapper = wrapper
        if field.wrapper is not None:
            field.wrapper.setToolTip(field.help + " " + field.timing)

    @staticmethod
    def _find_layout_item(layout, target):
        index = layout.indexOf(target)
        if index >= 0:
            return layout, index
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.layout():
                found = SettingsWidget._find_layout_item(item.layout(), target)
                if found:
                    return found
            if item.widget() and item.widget().layout():
                found = SettingsWidget._find_layout_item(item.widget().layout(), target)
                if found:
                    return found
        return None

    @staticmethod
    def _default_text(field):
        if field.key == "hf_token" or field.key == "gemini_key":
            return "empty"
        if field.key.startswith("prompt_"):
            return "built-in template"
        if field.key == "recording_guardian/duration_reminder_seconds":
            return f"{int(field.default) // 60} minutes"
        if field.key == "recording_guardian/silence_warning_seconds":
            return f"{int(field.default) // 60} minutes"
        if field.key == "ollama_model":
            return "no model selected"
        if field.key == "ai_provider":
            return "Google Gemini"
        if len(field.keys) == 2:
            return "System default"
        return str(field.default)

    def _prepare_static_controls(self):
        g = self.general_panel
        self._static_by_category = {
            "AI & chat": [g.gemini_widget, g.ollama_widget],
            "Search & knowledge": [self.rag_actions_widget],
            "Automation & notifications": [g.check_update_btn, g.updater_status_label],
            "Integrations": [g.copy_mcp_config_btn, g.mcp_status_label, g.repair_shortcuts_btn],
        }
        for category, widgets in self._static_by_category.items():
            for item in widgets:
                item.setProperty("settingsCategory", category)

        # Existing section headings and explanatory copy are grouped with their
        # owning fields so category filtering never leaves orphaned headers.
        for panel in (
            self.general_panel, self.audio_panel, self.rag_panel,
            self.prompts_panel, self.productivity_panel,
        ):
            for label in panel.findChildren(QLabel):
                text = label.text().casefold()
                if any(word in text for word in ("ai provider", "hugging face", "summary", "prompt", "ollama")):
                    category = "AI & chat" if panel is self.general_panel or panel is self.prompts_panel else None
                    if category and not label.property("settingsCategory"):
                        label.setProperty("settingsCategory", category)
                if panel is self.audio_panel and any(word in text for word in ("recording settings", "recording safety", "these settings affect")):
                    label.setProperty("settingsCategory", "Recording & devices")
                if panel is self.audio_panel and "transcription engine" in text:
                    label.setProperty("settingsCategory", "Transcription & speakers")
                if panel is self.audio_panel and "advanced device detection" in text:
                    label.setProperty("settingsCategory", "Recording & devices")
                if panel is self.rag_panel:
                    label.setProperty("settingsCategory", "Search & knowledge")
                if panel is self.prompts_panel:
                    label.setProperty("settingsCategory", "AI & chat")
                if panel is self.general_panel:
                    if "local rest api" in text or "model context protocol" in text or "os integration" in text:
                        label.setProperty("settingsCategory", "Integrations")
                    elif "auto-updater" in text:
                        label.setProperty("settingsCategory", "Automation & notifications")

    def _set_advanced(self, enabled, *, persist=True):
        self._advanced = bool(enabled)
        if hasattr(self, "advanced_toggle"):
            self.advanced_toggle.blockSignals(True)
            self.advanced_toggle.setChecked(self._advanced)
            self.advanced_toggle.blockSignals(False)
        if persist:
            self.settings.setValue("settings/advanced_mode", self._advanced)
        if hasattr(self, "catalog"):
            self._apply_visibility()
        if hasattr(self, "advanced_summary"):
            names = [field.label for field in self.catalog if field.advanced]
            self.advanced_summary.setText(
                "Advanced mode includes: " + ", ".join(names[:7]) + (" and more." if len(names) > 7 else ".")
                if not self._advanced else "Advanced settings are shown in their owning categories."
            )
            self.advanced_summary.setVisible(not self._advanced)

    def _show_category(self, category):
        if category not in CATEGORIES:
            return
        self._category = category
        self._restoring_category = True
        self.category_list.setCurrentRow(CATEGORIES.index(category))
        self._restoring_category = False
        self.category_summary.setText(CATEGORY_SUMMARIES[category])
        self.settings.setValue("settings/category", category)
        self._apply_visibility()

    def _apply_visibility(self):
        if not hasattr(self, "catalog"):
            return
        category = self._search_override or self._category
        visible_panels = set()
        for field in self.catalog:
            show = field.category == category and (self._advanced or not field.advanced)
            if field.wrapper:
                field.wrapper.setVisible(show)
            if field.row_label:
                field.row_label.setVisible(show)
            if show:
                visible_panels.add(field.owner)
        for panel in (
            self.general_panel, self.audio_panel, self.rag_panel,
            self.prompts_panel, self.productivity_panel,
        ):
            panel.setVisible(panel in visible_panels)
        for group, widgets in self._static_by_category.items():
            for item in widgets:
                item.setVisible(group == category)
        for panel in (
            self.general_panel, self.audio_panel, self.rag_panel,
            self.prompts_panel, self.productivity_panel,
        ):
            for item in panel.findChildren(QWidget):
                item_category = item.property("settingsCategory")
                if item_category:
                    item_advanced = bool(item.property("settingsAdvanced"))
                    item.setVisible(
                        item_category == category and (self._advanced or not item_advanced)
                    )
        self.general_panel.gemini_widget.setVisible(category == "AI & chat")
        self.general_panel.ollama_widget.setVisible(category == "AI & chat")
        if hasattr(self, "rag_actions_widget"):
            self.rag_actions_widget.setVisible(category == "Search & knowledge")
        self._update_advanced_summary()

    def _update_advanced_summary(self):
        if not self._advanced:
            active = []
            for field in self.catalog:
                if not field.advanced:
                    continue
                value = field.control
                if field.key in {"hf_token", "gemini_key"}:
                    configured = bool(value.text().strip())
                    if configured:
                        active.append(field.label + " configured")
                    continue
                if isinstance(value, QCheckBox):
                    active_value = value.isChecked()
                elif hasattr(value, "currentText"):
                    active_value = value.currentText()
                    active_value = active_value not in ("", "auto", str(field.default))
                elif hasattr(value, "text"):
                    active_value = value.text().strip()
                    active_value = active_value not in ("", str(field.default))
                else:
                    active_value = False
                if active_value:
                    active.append(field.label)
            summary = ", ".join(active[:5])
            if len(active) > 5:
                summary += f", and {len(active) - 5} more"
            self.advanced_summary.setText(
                "Advanced choices in use: " + (summary + "." if summary else "none.")
                + " Enable Advanced settings to review them."
            )
            self.advanced_summary.show()
        else:
            self.advanced_summary.hide()

    def _on_category_changed(self, row):
        if self._restoring_category or row < 0:
            return
        requested = CATEGORIES[row]
        if requested == self._category:
            return
        if self.has_unsaved_changes() and not self._resolve_pending_edits():
            self._restoring_category = True
            self.category_list.setCurrentRow(CATEGORIES.index(self._category))
            self._restoring_category = False
            return
        self._show_category(requested)

    def _update_search_results(self, query):
        query = query.strip().casefold()
        if not query:
            self.search_results.clear()
            self.search_results.hide()
            self.category_list.setEnabled(True)
            self._search_override = None
            self._show_category(self._previous_search_category)
            return
        if not self.search_results.isVisible():
            self._previous_search_category = self._category
        self.search_results.clear()
        for field in self.catalog:
            if query in field.search_text():
                item = QListWidgetItem(f"{field.label}  ·  {field.category}")
                item.setData(Qt.ItemDataRole.UserRole, field.key)
                item.setToolTip(field.help)
                self.search_results.addItem(item)
        self.search_results.setVisible(self.search_results.count() > 0)
        self.category_list.setEnabled(False)
        if self.search_results.count() == 0:
            self.search_results.addItem("No settings found. Try another keyword.")
            self.search_results.show()

    def _open_search_result(self, item):
        key = item.data(Qt.ItemDataRole.UserRole)
        field = next((candidate for candidate in self.catalog if candidate.key == key), None)
        if field is None:
            return
        self._search_override = field.category
        if field.advanced and not self._advanced:
            self._set_advanced(True)
        self.category_summary.setText(CATEGORY_SUMMARIES[field.category])
        self._apply_visibility()
        # A result can point into the currently inactive AI provider section.
        for parent in (field.view, field.control):
            current = parent
            while current is not None and current is not self.surface:
                current.setVisible(True)
                current = current.parentWidget()
        self.category_list.blockSignals(True)
        self.category_list.setCurrentRow(CATEGORIES.index(field.category))
        self.category_list.blockSignals(False)
        self.surface_scroll.ensureWidgetVisible(field.wrapper or field.control)
        field.control.setFocus(Qt.FocusReason.OtherFocusReason)
        QTimer.singleShot(0, lambda control=field.control: control.setFocus(Qt.FocusReason.OtherFocusReason))

    def open_setting(self, key):
        """Open a canonical setting from a workflow-specific deep link."""
        field = next((candidate for candidate in self.catalog if key in candidate.keys), None)
        if field is None:
            return False
        if field.category != self._category and self.has_unsaved_changes():
            if not self._resolve_pending_edits():
                return False
        if self.search_input.text():
            self.search_input.clear()
        if field.advanced and not self._advanced:
            self._set_advanced(True)
        self._show_category(field.category)
        for current in (field.view, field.control):
            parent = current
            while parent is not None and parent is not self.surface:
                parent.setVisible(True)
                parent = parent.parentWidget()
        self.surface_scroll.ensureWidgetVisible(field.wrapper or field.control)
        field.control.setFocus(Qt.FocusReason.OtherFocusReason)
        QTimer.singleShot(0, lambda control=field.control: control.setFocus(Qt.FocusReason.OtherFocusReason))
        return True

    def _stage_all(self):
        self.overlay.clear()
        self.general_panel.save(apply_runtime=False)
        self.audio_panel.save()
        self.rag_panel.save()
        self.prompts_panel.save()
        self.productivity_panel.save()

    def _changes(self):
        self._stage_all()
        changes = self.overlay.changes(self.defaults)
        baseline = getattr(self, "_baseline_values", {})
        return {
            key: value for key, value in changes.items()
            if key not in baseline or baseline[key] != value
        }

    def has_unsaved_changes(self):
        return bool(self._changes())

    def _refresh_dirty_state(self):
        changes = self._changes()
        dirty = bool(changes)
        self._set_validation_errors(self._validate_changes(changes))
        self.discard_btn.setEnabled(dirty)
        self.save_btn.setEnabled(dirty)
        return dirty

    def _set_validation_errors(self, errors):
        for field in self.catalog:
            message = next((errors[key] for key in field.keys if key in errors), "")
            if message:
                message += " Saved value remains unchanged; correct it and retry."
            if field.error_label is not None:
                field.error_label.setText(message)
                field.error_label.setVisible(bool(message))

    def _validate_changes(self, changes):
        errors = {}
        for field in self.catalog:
            for key in field.keys:
                if key not in changes or not field.validator:
                    continue
                try:
                    message = field.validator(changes[key])
                except (TypeError, ValueError):
                    message = "Enter a valid value."
                if message:
                    errors[key] = message
        if changes.get("ai_provider") == "ollama":
            model = changes.get("ollama_model", self.settings.value("ollama_model", ""))
            if not str(model).strip():
                errors["ai_provider"] = "Choose an Ollama model before switching to that provider."
        return errors

    def save_settings(self):
        """Validate and persist changed keys only, preserving unrelated values."""
        changes = self._changes()
        if not changes:
            self.status_label.setText("No changed settings to save.")
            self._refresh_dirty_state()
            return True
        errors = self._validate_changes(changes)
        invalid_keys = set(errors)
        valid = {key: value for key, value in changes.items() if key not in invalid_keys}
        previous_values = {
            key: self.settings.value(key, self.defaults.get(key))
            for key in valid
        }
        for key, value in valid.items():
            self.settings.setValue(key, value)
        self.settings.sync()
        if getattr(self.settings.status(), "value", self.settings.status()) != 0:
            self.status_label.setText(
                "Settings could not be written to storage. The previous saved values remain active; retry Save."
            )
            return False

        if valid:
            apply_keys = set(valid) | set(self._apply_retry_keys)
            self._apply_retry_keys = self.general_panel.apply_saved_runtime(apply_keys)
            self.apply_retry_btn.setVisible(bool(self._apply_retry_keys))
        changed_restart = RESTART_KEYS.intersection(valid)
        for key in changed_restart:
            active_value = self._pending_restart_values.get(key, previous_values[key])
            if valid[key] == active_value:
                self._pending_restart_keys.discard(key)
                self._pending_restart_values.pop(key, None)
            else:
                self._pending_restart_keys.add(key)
                self._pending_restart_values[key] = active_value
        if changed_restart:
            if self._pending_restart_keys:
                self.settings.setValue("settings/pending_restart_keys", sorted(self._pending_restart_keys))
                self.settings.setValue(
                    "settings/pending_restart_values",
                    json.dumps(self._pending_restart_values, sort_keys=True),
                )
                self.settings.setValue("settings/pending_restart_pid", os.getpid())
            else:
                self.settings.remove("settings/pending_restart_keys")
                self.settings.remove("settings/pending_restart_values")
                self.settings.remove("settings/pending_restart_pid")
            self.settings.sync()

        saved_names = self._names_for_keys(valid)
        error_names = [self._name_for_key(key) for key in errors]
        parts = []
        if saved_names:
            parts.append("Saved: " + ", ".join(saved_names) + ".")
        if getattr(self, "_apply_retry_keys", None):
            parts.append(
                "Saved, but not active yet: "
                + ", ".join(self._names_for_keys(self._apply_retry_keys))
                + ". Retry applying or keep using the previous active values."
            )
        if error_names:
            parts.append("Needs correction: " + ", ".join(error_names) + ".")
        self.status_label.setText(
            "Settings saved successfully. " + " ".join(parts)
            if saved_names else " ".join(parts) or "No valid changed settings were saved."
        )
        self.status_label.setAccessibleName("Settings save result")
        self.overlay.clear()
        self._baseline_values.update(valid)
        self._refresh_dirty_state()
        self._refresh_restart_status()
        return not errors

    def _retry_runtime_apply(self):
        keys = set(getattr(self, "_apply_retry_keys", set()))
        if not keys:
            self.apply_retry_btn.hide()
            return
        self._apply_retry_keys = self.general_panel.apply_saved_runtime(keys)
        self.apply_retry_btn.setVisible(bool(self._apply_retry_keys))
        if self._apply_retry_keys:
            self.status_label.setText(
                "Saved values remain inactive: "
                + ", ".join(self._names_for_keys(self._apply_retry_keys))
                + ". Retry after correcting the runtime issue."
            )
        else:
            self.status_label.setText("Saved settings are now active.")

    def _names_for_keys(self, keys):
        names = []
        for key in keys:
            name = self._name_for_key(key)
            if name not in names:
                names.append(name)
        return names

    def _name_for_key(self, key):
        field = next((item for item in self.catalog if key in item.keys), None)
        return field.label if field else key

    def discard_settings(self):
        category = self._category
        self.overlay.clear()
        self._build_panels()
        self._stage_all()
        self._baseline_values = dict(self.overlay._values)
        self._show_category(category)
        self._apply_visibility()
        self.status_label.setText("Unsaved changes discarded.")
        self._refresh_dirty_state()

    def _ask_dirty_decision(self):
        box = QMessageBox(self)
        box.setWindowTitle("Unsaved settings")
        box.setText("Save your changes before leaving this category?")
        box.setInformativeText("Save applies valid edits; Discard restores saved values.")
        save = box.addButton("Save", QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton("Discard", QMessageBox.ButtonRole.DestructiveRole)
        stay = box.addButton("Stay", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(save)
        box.exec()
        clicked = box.clickedButton()
        return "save" if clicked is save else "discard" if clicked is discard else "stay"

    def _resolve_pending_edits(self):
        if not self.has_unsaved_changes():
            return True
        decision = self._leave_decision or self._ask_dirty_decision()
        self._leave_decision = None
        if decision == "save":
            return self.save_settings()
        if decision == "discard":
            self.discard_settings()
            return True
        return False

    def request_leave(self):
        """Return whether the owner may navigate away or close this tab."""
        return self._resolve_pending_edits()

    def _reset_category(self):
        fields = [field for field in self.catalog if field.category == self._category]
        labels = "\n".join(f"• {field.label}" for field in fields)
        result = QMessageBox.question(
            self,
            "Reset category",
            f"Reset these settings to their defaults?\n\n{labels}\n\nOther categories will remain unchanged.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if result != QMessageBox.StandardButton.Yes:
            return
        for field in fields:
            field.reset()
        self._refresh_dirty_state()
        self.status_label.setText(f"{self._category} defaults staged. Save to apply them.")

    def _load_pending_restart(self):
        keys = set(self.settings.value("settings/pending_restart_keys", [], type=list) or [])
        previous_pid = self.settings.value("settings/pending_restart_pid", None)
        if keys and previous_pid is not None and str(previous_pid) != str(os.getpid()):
            self.settings.remove("settings/pending_restart_keys")
            self.settings.remove("settings/pending_restart_values")
            self.settings.remove("settings/pending_restart_pid")
            self.settings.sync()
            return set(), {}
        try:
            values = json.loads(self.settings.value("settings/pending_restart_values", "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            values = {}
        return keys, values

    def _refresh_restart_status(self):
        details = []
        for key in sorted(self._pending_restart_keys):
            label = self._name_for_key(key)
            saved = self.settings.value(key, self.defaults.get(key))
            active = self._pending_restart_values.get(key, self.defaults.get(key))
            details.append(f"{label}: saved {saved}; active until restart {active}")
        self.restart_status_label.setText(
            "Restart required. " + "; ".join(details) + "."
            if details else ""
        )
        self.restart_btn.setVisible(bool(details))

    def _request_restart(self):
        reply = QMessageBox.question(
            self,
            "Restart application",
            "Restart now to apply the saved startup settings?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        window = self.window()
        restart = getattr(window, "restart_app", None)
        if callable(restart):
            restart()
        else:
            self.status_label.setText("Restart El Secretario to apply these settings.")

    def _save_rag_settings(self):
        self.overlay.clear()
        self.rag_panel.save()
        changed = self.overlay.changes(self.defaults)
        rag_keys = {
            "rag_enabled", "rag_persist_directory", "rag_safe_delete_mode",
            "rag_subprocess_upsert_mode", "rag_subprocess_query_mode",
        }
        changed = {key: value for key, value in changed.items() if key in rag_keys}
        errors = self._validate_changes(changed)
        if errors:
            self.status_label.setText("Needs correction: " + ", ".join(self._names_for_keys(errors)) + ".")
            return False
        for key, value in changed.items():
            self.settings.setValue(key, value)
        self.settings.sync()
        if getattr(self.settings.status(), "value", self.settings.status()) != 0:
            self.status_label.setText(
                "RAG options could not be written to storage. The previous saved values remain active; retry the action."
            )
            return False
        self.overlay.clear()
        self._refresh_dirty_state()
        return True

    def _initialize_rag(self):
        if not self._save_rag_settings():
            return
        self.rag_initialize_requested.emit(self.rag_panel.get_rag_config())
        self.status_label.setText("RAG initialize requested using saved options.")

    def _reload_rag(self):
        if not self._save_rag_settings():
            return
        self.rag_reload_requested.emit(self.rag_panel.get_rag_config())
        self.status_label.setText("RAG reload requested using saved options.")

    def _queue_rag_reindex(self):
        self.rag_reindex_requested.emit()
        self.status_label.setText("RAG reindex task queued.")

    def _clear_status_label(self):
        self.status_label.clear()
