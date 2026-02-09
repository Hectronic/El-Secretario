# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Unified Tools Widget combining Maintenance and Batch Processing functionality.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QLabel)
from PyQt6.QtCore import Qt

from src.ui.maintenance_widget import MaintenanceWidget
from src.ui.batch_process_widget import BatchProcessWidget
from src.ui.summary_batch_widget import SummaryBatchWidget


class ToolsWidget(QWidget):
    """
    Unified widget that combines Storage management, Batch Processing, 
    and Data Export/Import into a single tabbed interface.
    """

    # Tab indices for external access
    TAB_STORAGE = 0
    TAB_PROCESSING = 1
    TAB_DATA = 2

    def __init__(self, db, notebook_db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.notebook_db = notebook_db
        
        self.init_ui()

    def init_ui(self):
        """Initialize the unified tools interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title = QLabel("⚙️ Tools")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #607D8B; padding: 20px;")
        layout.addWidget(title)

        # Create tab widget for sub-sections
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444;
                border-radius: 5px;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #3a3a3a;
                color: #aaa;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #2b2b2b;
                color: #fff;
            }
            QTabBar::tab:hover {
                background-color: #4a4a4a;
            }
        """)

        # Storage Tab (from MaintenanceWidget - cleanup functionality)
        self.storage_widget = self._create_storage_tab()
        self.tabs.addTab(self.storage_widget, "🗄️ Storage")

        # Processing Tab (from BatchProcessWidget)
        self.processing_widget = BatchProcessWidget()
        self.tabs.addTab(self.processing_widget, "⏳ Processing")

        # Summary Tab (New)
        self.summary_widget = SummaryBatchWidget()
        self.tabs.addTab(self.summary_widget, "📝 Summaries")

        # Data Tab (from MaintenanceWidget - export/import)
        self.data_widget = self._create_data_tab()
        self.tabs.addTab(self.data_widget, "📦 Data")

        layout.addWidget(self.tabs)

    def _create_storage_tab(self):
        """Create the Storage tab with cleanup functionality."""
        # Reuse MaintenanceWidget but it contains both storage and data sections
        # We'll create a full maintenance widget and it will show all its content
        widget = MaintenanceWidget(self.db, self.notebook_db)
        return widget

    def _create_data_tab(self):
        """Create the Data tab with export/import functionality."""
        # For now, we'll show a simplified reference since MaintenanceWidget 
        # already has export/import built in
        from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QMessageBox, QFileDialog
        from src.data_export import DataExporter
        import logging
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(40, 40, 40, 40)

        # Title
        title = QLabel("Data Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #607D8B;")
        layout.addWidget(title)

        # Info
        info = QLabel(
            "Export all your conversations, transcriptions, notebooks, and chat sessions to a JSON file. "
            "Audio files are NOT exported (only transcriptions and metadata). "
            "Import will detect and skip duplicates."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #aaa; font-size: 14px;")
        layout.addWidget(info)

        # Status Label
        self.data_status_lbl = QLabel("")
        self.data_status_lbl.setWordWrap(True)
        self.data_status_lbl.setStyleSheet("color: #4CAF50; font-size: 14px;")
        layout.addWidget(self.data_status_lbl)

        # Buttons
        btn_layout = QHBoxLayout()
        
        self.export_btn = QPushButton("Export All Data")
        self.export_btn.setFixedSize(180, 50)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 15px;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        self.export_btn.clicked.connect(self._export_data)
        btn_layout.addWidget(self.export_btn)

        self.import_btn = QPushButton("Import Data")
        self.import_btn.setFixedSize(180, 50)
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                font-size: 15px;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        self.import_btn.clicked.connect(self._import_data)
        btn_layout.addWidget(self.import_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        
        return widget

    def _export_data(self):
        """Export all data to a JSON file."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from src.data_export import DataExporter
        import logging
        
        logger = logging.getLogger(__name__)
        
        if not self.notebook_db:
            QMessageBox.warning(self, "Error", "Notebook database not available.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Data", "el_secretario_export.json", "JSON Files (*.json)"
        )
        
        if not file_path:
            return

        try:
            self.export_btn.setEnabled(False)
            self.export_btn.setText("Exporting...")
            self.data_status_lbl.setText("")
            
            exporter = DataExporter(self.db, self.notebook_db)
            stats = exporter.export_all(file_path)
            
            status_msg = (
                f"✓ Export complete! Saved to: {file_path}\n"
                f"Records: {stats['records_count']}, "
                f"Chat Sessions: {stats['chat_sessions_count']}, "
                f"Notebooks: {stats['notebooks_count']}"
            )
            self.data_status_lbl.setText(status_msg)
            self.data_status_lbl.setStyleSheet("color: #4CAF50; font-size: 14px;")
            logger.info(f"Export complete: {stats}")
            
            QMessageBox.information(
                self, "Export Complete",
                f"Data exported successfully!\n\n"
                f"Records: {stats['records_count']}\n"
                f"Chat Sessions: {stats['chat_sessions_count']}\n"
                f"Notebooks: {stats['notebooks_count']}"
            )
            
        except Exception as e:
            logger.error(f"Export failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Export Failed", f"An error occurred: {e}")
            self.data_status_lbl.setText(f"✗ Export failed: {e}")
            self.data_status_lbl.setStyleSheet("color: #f44336; font-size: 14px;")
        finally:
            self.export_btn.setEnabled(True)
            self.export_btn.setText("Export All Data")

    def _import_data(self):
        """Import data from a JSON file."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from src.data_export import DataExporter
        import logging
        
        logger = logging.getLogger(__name__)
        
        if not self.notebook_db:
            QMessageBox.warning(self, "Error", "Notebook database not available.")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Data", "", "JSON Files (*.json)"
        )
        
        if not file_path:
            return

        reply = QMessageBox.question(
            self, "Confirm Import",
            "This will import data from the selected file. "
            "Existing data will NOT be overwritten (duplicates will be skipped).\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self.import_btn.setEnabled(False)
            self.import_btn.setText("Importing...")
            self.data_status_lbl.setText("")
            
            exporter = DataExporter(self.db, self.notebook_db)
            result = exporter.import_all(file_path)
            
            if not result.success:
                raise Exception(result.error_message)
            
            status_msg = (
                f"✓ Import complete!\n"
                f"Records: {result.records.imported} imported, {result.records.skipped} skipped\n"
                f"Chat Sessions: {result.chat_sessions.imported} imported, {result.chat_sessions.skipped} skipped\n"
                f"Notebooks: {result.notebooks.imported} imported, {result.notebooks.skipped} skipped"
            )
            self.data_status_lbl.setText(status_msg)
            self.data_status_lbl.setStyleSheet("color: #4CAF50; font-size: 14px;")
            logger.info(f"Import complete: records={result.records}, sessions={result.chat_sessions}, notebooks={result.notebooks}")
            
            QMessageBox.information(
                self, "Import Complete",
                f"Data imported successfully!\n\n"
                f"Records: {result.records.imported} imported, {result.records.skipped} skipped\n"
                f"Chat Sessions: {result.chat_sessions.imported} imported, {result.chat_sessions.skipped} skipped\n"
                f"Notebooks: {result.notebooks.imported} imported, {result.notebooks.skipped} skipped"
            )
            
            # Refresh storage stats
            if hasattr(self.storage_widget, 'calculate_stats'):
                self.storage_widget.calculate_stats()
            
        except Exception as e:
            logger.error(f"Import failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Import Failed", f"An error occurred: {e}")
            self.data_status_lbl.setText(f"✗ Import failed: {e}")
            self.data_status_lbl.setStyleSheet("color: #f44336; font-size: 14px;")
        finally:
            self.import_btn.setEnabled(True)
            self.import_btn.setText("Import Data")

    def show_tab(self, tab_index):
        """Switch to a specific tab."""
        if 0 <= tab_index < self.tabs.count():
            self.tabs.setCurrentIndex(tab_index)
