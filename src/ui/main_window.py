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

import os
import re
import shutil
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QListWidget, QPushButton, 
                             QLabel, QMessageBox, QListWidgetItem, QComboBox,
                             QTabWidget, QSplitter, QApplication, QStyle, QLineEdit, QTabBar,
                             QCalendarWidget, QCheckBox, QFileDialog, QMenu)
from PyQt6.QtCore import Qt, QSettings, QUrl
from PyQt6.QtGui import QCursor, QAction, QIcon

from src.database import DBManager
from src.audio import Recorder
from src.worker import SearchThread
from src.ui.dialogs import SettingsDialog
from src.ui.welcome_widget import WelcomeWidget
from src.ui.recording_widget import RecordingWidget
from src.ui.recording_in_progress_widget import RecordingInProgressWidget
from src.ui.search_results_widget import SearchResultsWidget
from src.ui.chat_widget import ChatWidget
from src.ui.collection_widget import CollectionWidget
from src.ui.calendar_widget import CalendarWidget
from src.ui.styles import LIST_WIDGET_STYLE, NEW_CHAT_BUTTON_STYLE
from src.ui.components import RecordingListItemWidget

from src.ui.batch_process_widget import BatchProcessWidget
from src.notebook_database import NotebookDBManager
from src.ui.notebooks_list_widget import NotebooksListWidget
from src.ui.notebook_widget import NotebookWidget
from src.ui.maintenance_widget import MaintenanceWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        import logging
        logging.info("Initializing MainWindow...")
        self.setWindowTitle("El Secretario")
        self.setWindowIcon(QIcon("logo.png"))
        self.resize(1300, 800)

        self.db = DBManager()
        self.notebook_db = NotebookDBManager()
        self.recorder = Recorder()
        # We can connect global recorder signals here if needed, 
        # but RecordingWidget handles its own UI updates.
        
        self.search_thread = None
        
        self.init_ui()
        self.load_history()
        self.refresh_tag_filter()
        self.load_history()
        self.refresh_tag_filter()
        self.load_chat_sessions()
        self.load_collections()
        
        # Show Welcome Tab
        self.show_welcome_screen()
        logging.info("MainWindow initialized.")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)

        # --- Left Panel: History & Search ---
        left_widget = QWidget()
        left_widget.setMinimumWidth(300) # Slightly wider for the custom items
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        # Search Box
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search recordings...")
        self.search_input.textChanged.connect(self.filter_history_list)
        search_layout.addWidget(self.search_input)
        left_layout.addLayout(search_layout)
        
        # Filter Row (Tags)
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        self.tag_filter_combo = QComboBox()
        self.tag_filter_combo.addItem("All")
        self.tag_filter_combo.currentTextChanged.connect(self.load_history)
        filter_layout.addWidget(self.tag_filter_combo)
        
        self.fav_filter_cb = QCheckBox("★")
        self.fav_filter_cb.setToolTip("Show Favorites Only")
        self.fav_filter_cb.stateChanged.connect(self.load_history)
        filter_layout.addWidget(self.fav_filter_cb)
        
        left_layout.addLayout(filter_layout)
        
        # History List
        self.history_list = QListWidget()
        self.history_list.setStyleSheet(LIST_WIDGET_STYLE)
        self.history_list.itemClicked.connect(self.on_history_item_clicked)
        left_layout.addWidget(self.history_list)


        # Settings Button
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.clicked.connect(self.open_settings)
        left_layout.addWidget(self.settings_btn)
        
        # Calendar Widget
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.selectionChanged.connect(self.on_calendar_date_changed)
        # Set a fixed height or max height so it doesn't take too much space
        self.calendar.setMaximumHeight(300)
        left_layout.addWidget(self.calendar)
        
        # Open Full Calendar Button
        self.open_calendar_btn = QPushButton("Open Full Calendar")
        self.open_calendar_btn.clicked.connect(self.open_calendar_tab)
        left_layout.addWidget(self.open_calendar_btn)
        
        # Reset Date Filter Button
        self.reset_date_btn = QPushButton("Show All Dates")
        self.reset_date_btn.clicked.connect(self.reset_date_filter)
        left_layout.addWidget(self.reset_date_btn)
        
        # Initialize date filter state
        self.current_date_filter = None

        self.splitter.addWidget(left_widget)

        # --- Middle Panel: Tabbed Interface ---
        self.central_tabs = QTabWidget()
        self.central_tabs.setTabsClosable(True)
        self.central_tabs.tabCloseRequested.connect(self.close_tab)
        self.central_tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.central_tabs.customContextMenuRequested.connect(self.show_tab_context_menu)
        self.splitter.addWidget(self.central_tabs)
        
        # --- Right Panel: Chat History & Collections ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_panel.setMinimumWidth(300) # Ensure it's at least this wide
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Chat History Section
        chat_hist_group = QWidget()
        chat_hist_layout = QVBoxLayout(chat_hist_group)
        chat_hist_layout.setContentsMargins(0, 0, 0, 0)
        
        chat_hist_layout.addWidget(QLabel("<b>Chat History</b>"))
        
        self.new_chat_btn = QPushButton("New Chat")
        self.new_chat_btn.clicked.connect(lambda: self.open_chat_tab(None))
        self.new_chat_btn.setStyleSheet(NEW_CHAT_BUTTON_STYLE)
        chat_hist_layout.addWidget(self.new_chat_btn)
        
        self.sessions_list = QListWidget()
        self.sessions_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) # No scrollbar
        self.sessions_list.setStyleSheet(LIST_WIDGET_STYLE)
        self.sessions_list.itemClicked.connect(self.on_chat_session_clicked)
        chat_hist_layout.addWidget(self.sessions_list)
        
        self.delete_chat_session_btn = QPushButton("Delete Chat")
        self.delete_chat_session_btn.setStyleSheet("color: #f44336;")
        self.delete_chat_session_btn.clicked.connect(self.delete_selected_chat_session)
        chat_hist_layout.addWidget(self.delete_chat_session_btn)
        
        right_layout.addWidget(chat_hist_group)
        
        # Collections Section
        right_layout.addWidget(QLabel("<b>Collections</b>"))
        
        self.collections_list = QListWidget()
        self.collections_list.setStyleSheet(LIST_WIDGET_STYLE)
        self.collections_list.itemClicked.connect(self.on_collection_clicked)
        right_layout.addWidget(self.collections_list)
        
        self.splitter.addWidget(right_panel)

        # Set initial sizes for the three panels
        # Left: 300 (min), Middle: 700 (rest), Right: 300 (min)
        self.splitter.setSizes([300, 700, 300])
        
        # Enforce stretch factors to ensure right panel takes up space
        self.splitter.setStretchFactor(0, 0) # Left panel doesn't stretch
        self.splitter.setStretchFactor(1, 1) # Middle panel stretches
        self.splitter.setStretchFactor(2, 0) # Right panel doesn't stretch
        
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        self.splitter.setCollapsible(2, False)
        
        # Initialize RAG Engine
        try:
            from src.rag_engine import RAGEngine
            self.rag = RAGEngine()
        except Exception as e:
            print(f"Failed to init RAG: {e}")
            self.rag = None

    def show_welcome_screen(self):
        self.welcome_widget = WelcomeWidget(self.db)
        self.welcome_widget.new_recording_requested.connect(self.start_new_recording)
        self.welcome_widget.search_triggered.connect(self.perform_welcome_search)
        self.welcome_widget.result_clicked.connect(self.open_recording_tab)
        self.welcome_widget.new_chat_requested.connect(lambda: self.open_chat_tab(None))
        self.welcome_widget.batch_process_requested.connect(self.open_batch_process_tab)
        self.welcome_widget.import_audio_requested.connect(self.import_audio_file)
        self.welcome_widget.notebooks_requested.connect(self.open_notebooks_list)
        self.welcome_widget.maintenance_requested.connect(self.open_maintenance_tab)
        
        # Add as first tab, not closable
        self.central_tabs.addTab(self.welcome_widget, "Welcome")
        self.central_tabs.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None) # Remove close button

    def start_new_recording(self, config):
        """Start a new recording with the given configuration."""
        import logging
        logging.info(f"Starting new recording with config: {config}")
        # Check if we have a recording in progress already
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, RecordingInProgressWidget):
                self.central_tabs.setCurrentIndex(i)
                return
        
        # Set device on recorder
        if config.get("device_index") is not None:
            self.recorder.set_device(config["device_index"])
        
        # New Recording Flow with config
        rec_widget = RecordingInProgressWidget(recorder=self.recorder, config=config)
        rec_widget.finished.connect(lambda path, cfg, w=rec_widget: self.on_recording_finished(path, cfg, w))
        rec_widget.cancelled.connect(lambda w=rec_widget: self.close_tab(self.central_tabs.indexOf(w)))
        
        index = self.central_tabs.addTab(rec_widget, "Recording...")
        self.central_tabs.setCurrentIndex(index)

    def open_recording_tab(self, record_id, config=None):
        """Open a recording tab for an existing record."""
        # Check if already open
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, RecordingWidget) and widget.current_record_id == record_id and record_id is not None:
                self.central_tabs.setCurrentIndex(i)
                return widget

        # Create new tab for existing recording
        rec_widget = RecordingWidget(self.rag, recorder=self.recorder, record_id=record_id)
        rec_widget.recording_saved.connect(self.load_history)
        rec_widget.close_requested.connect(lambda: self.close_tab(self.central_tabs.indexOf(rec_widget)))
        
        # If config is provided, set the widget's transcription settings
        if config:
            rec_widget.set_transcription_config(config)
        
        title = "New Recording"
        if record_id:
            records = self.db.fetch_all()
            record = next((r for r in records if r['id'] == record_id), None)
            if record:
                title = record['title'] if record['title'] else f"Recording {record['id']}"
        
        index = self.central_tabs.addTab(rec_widget, title)
        self.central_tabs.setCurrentIndex(index)
        return rec_widget

    def on_recording_finished(self, file_path, config, widget):
        """Handle recording finished - save to DB and start transcription with config."""
        # Close the recording widget
        index = self.central_tabs.indexOf(widget)
        if index != -1:
            self.central_tabs.removeTab(index)
            widget.deleteLater()
        
        try:
            filename = os.path.basename(file_path)
            # Create DB entry to get an ID
            record_id = self.db.save(filename, "", 0.0, title=filename)
            
            # Open standard recording tab with config
            rec_widget = self.open_recording_tab(record_id, config)
            
            # Trigger transcription with config
            if rec_widget and isinstance(rec_widget, RecordingWidget):
                rec_widget.start_transcription_with_config(file_path, config)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save recording: {e}")

    def open_chat_tab(self, session_id=None, initial_contexts=None):
        if not self.rag:
            QMessageBox.warning(self, "RAG Error", "RAG Engine not initialized.")
            return
        
        # Check if already open (only for sessions)
        if session_id:
            for i in range(self.central_tabs.count()):
                widget = self.central_tabs.widget(i)
                if isinstance(widget, ChatWidget):
                    if widget.current_session_id == session_id:
                        self.central_tabs.setCurrentIndex(i)
                        return

        chat_widget = ChatWidget(self.rag, session_id, self, initial_contexts=initial_contexts)
        chat_widget.session_updated.connect(self.load_chat_sessions)
        
        title = "New Chat"
        if session_id:
            sessions = self.db.fetch_chat_sessions()
            session = next((s for s in sessions if s['id'] == session_id), None)
            if session:
                title = session['name']
        elif initial_contexts:
            labels = [c['label'] for c in initial_contexts]
            title = f"Chat: {', '.join(labels)}"
        
        index = self.central_tabs.addTab(chat_widget, title)
        self.central_tabs.setCurrentIndex(index)

    def open_batch_process_tab(self):
        # Check if already open
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, BatchProcessWidget):
                self.central_tabs.setCurrentIndex(i)
                return

        batch_widget = BatchProcessWidget()
        # Connect finished signal if we want to do something, e.g. reload history
        # batch_widget.finished.connect(self.load_history) 
        
        index = self.central_tabs.addTab(batch_widget, "Batch Processing")
        self.central_tabs.setCurrentIndex(index)

    def close_tab(self, index):
        widget = self.central_tabs.widget(index)
        if isinstance(widget, WelcomeWidget):
             # Maybe don't allow closing welcome widget?
             return 
        if isinstance(widget, RecordingWidget):
             # Check for unsaved changes? 
             # For now, RecordingWidget handles its own cleanup/saving via signals mostly.
             # But if we close it forcefully, we might lose unsaved title/tags if not saved.
             # Ideally call a method on widget to check.
             pass
             
        self.central_tabs.removeTab(index)
        widget.deleteLater()
        
        if self.central_tabs.count() == 0:
            self.show_welcome_screen()

    def show_tab_context_menu(self, point):
        index = self.central_tabs.tabBar().tabAt(point)
        if index == -1:
            return

        menu = QMenu(self)
        
        close_action = QAction("Close", self)
        close_action.triggered.connect(lambda: self.close_tab(index))
        menu.addAction(close_action)
        
        close_others_action = QAction("Close Others", self)
        close_others_action.triggered.connect(lambda: self.close_other_tabs(index))
        menu.addAction(close_others_action)
        
        close_all_action = QAction("Close All", self)
        close_all_action.triggered.connect(self.close_all_tabs)
        menu.addAction(close_all_action)
        
        menu.exec(self.central_tabs.mapToGlobal(point))

    def close_other_tabs(self, keep_index):
        # We need to be careful with indices shifting.
        # Strategy: Iterate backwards and close if index != keep_index
        count = self.central_tabs.count()
        for i in range(count - 1, -1, -1):
            if i != keep_index:
                self.close_tab(i)

    def close_all_tabs(self):
        count = self.central_tabs.count()
        for i in range(count - 1, -1, -1):
            self.close_tab(i)
        
        if self.central_tabs.count() == 0:
            self.show_welcome_screen()

    def load_history(self):
        self.history_list.clear()
        tag_filter = self.tag_filter_combo.currentText()
        favorites_only = self.fav_filter_cb.isChecked()
        
        if self.current_date_filter:
            tags = [tag_filter] if tag_filter != "All" else None
            records = self.db.fetch_by_date_range(self.current_date_filter, self.current_date_filter, tags, favorites_only=favorites_only)
        else:
            records = self.db.fetch_all(tag_filter=tag_filter, favorites_only=favorites_only)
            
        for record in records:
            item = QListWidgetItem(self.history_list)
            widget = RecordingListItemWidget(record)
            item.setSizeHint(widget.sizeHint())
            
            widget.favorite_toggled.connect(lambda checked, r_id=record['id']: self.on_favorite_toggled(r_id, checked))
            widget.delete_requested.connect(lambda r_id=record['id']: self.delete_recording(r_id))
            
            self.history_list.addItem(item)
            self.history_list.setItemWidget(item, widget)
            item.setData(Qt.ItemDataRole.UserRole, record) # Still store data for click handler
            
        # Re-apply search filter if any
        self.filter_history_list(self.search_input.text())
        
        # Refresh welcome screen lists if it exists
        if hasattr(self, 'welcome_widget') and self.welcome_widget:
            try:
                self.welcome_widget.load_favorites()
                self.welcome_widget.load_today()
            except Exception as e:
                print(f"Error refreshing welcome widget: {e}")

    def refresh_tag_filter(self):
        current_tag = self.tag_filter_combo.currentText()
        self.tag_filter_combo.blockSignals(True)
        self.tag_filter_combo.clear()
        self.tag_filter_combo.addItem("All")
        
        if self.current_date_filter:
            # Fetch records for this date to get relevant tags
            records = self.db.fetch_by_date_range(self.current_date_filter, self.current_date_filter)
            tags = set()
            for r in records:
                if r['tags']:
                    tags.update([t.strip() for t in r['tags'].split(',') if t.strip()])
            sorted_tags = sorted(list(tags))
        else:
            sorted_tags = self.db.get_all_tags()
            
        self.tag_filter_combo.addItems(sorted_tags)
        
        index = self.tag_filter_combo.findText(current_tag)
        if index >= 0:
            self.tag_filter_combo.setCurrentIndex(index)
        else:
            self.tag_filter_combo.setCurrentIndex(0)
        self.tag_filter_combo.blockSignals(False)
        self.load_collections() # Also refresh collections list

    def load_collections(self):
        self.collections_list.clear()
        tags = self.db.get_all_tags()
        self.collections_list.addItems(tags)

    def on_collection_clicked(self, item):
        tag = item.text()
        self.open_collection_tab(tag)

    def open_collection_tab(self, tag):
        # Check if already open
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, CollectionWidget) and widget.tag == tag:
                self.central_tabs.setCurrentIndex(i)
                return

        col_widget = CollectionWidget(tag)
        col_widget.open_recording.connect(self.open_recording_tab)
        col_widget.start_chat.connect(self.open_collection_chat)
        
        index = self.central_tabs.addTab(col_widget, f"Collection: {tag}")
        self.central_tabs.setCurrentIndex(index)

    def open_collection_chat(self, tag):
        self.open_chat_tab(initial_contexts=[{"type": "tag", "value": tag, "label": tag}])

    def open_calendar_tab(self):
        # Check if already open
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, CalendarWidget):
                self.central_tabs.setCurrentIndex(i)
                return

        cal_widget = CalendarWidget(self.rag)
        cal_widget.start_chat_requested.connect(self.open_chat_tab_with_filters)
        
        index = self.central_tabs.addTab(cal_widget, "Calendar")
        self.central_tabs.setCurrentIndex(index)



    def open_chat_tab_with_filters(self, date_str, tags):
        contexts = []
        if date_str:
            contexts.append({"type": "date", "value": date_str, "label": date_str})
        if tags:
            for tag in tags:
                contexts.append({"type": "tag", "value": tag, "label": tag})
        self.open_chat_tab(initial_contexts=contexts)

    def on_history_item_clicked(self, item):
        record = item.data(Qt.ItemDataRole.UserRole)
        self.open_recording_tab(record['id'])



    def perform_welcome_search(self, query):
        if not self.rag:
            QMessageBox.warning(self, "RAG Error", "RAG Engine not initialized.")
            return
            
        if not query:
            return
            
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        
        # Reuse SearchThread
        # Reuse SearchThread
        self.search_thread = SearchThread(self.rag, query)
        self.search_thread.finished.connect(lambda results: self.on_search_finished_new_tab(results, query))
        self.search_thread.error.connect(self.on_search_error)
        self.search_thread.start()

    def on_search_finished_new_tab(self, results, query):
        QApplication.restoreOverrideCursor()
        
        # Create Search Results Widget
        search_widget = SearchResultsWidget(query)
        search_widget.display_results(results)
        search_widget.result_clicked.connect(self.open_recording_tab)
        
        # Add to tabs
        index = self.central_tabs.addTab(search_widget, f"Search: {query}")
        self.central_tabs.setCurrentIndex(index)

    def on_search_error(self, error_message):
        QApplication.restoreOverrideCursor()
        QMessageBox.critical(self, "Search Error", f"An error occurred during search: {error_message}")

    def load_chat_sessions(self):
        self.sessions_list.clear()
        sessions = self.db.fetch_chat_sessions()
        for s in sessions:
            item = QListWidgetItem(f"{s['name']} ({s['created_at'][:16]})")
            item.setData(Qt.ItemDataRole.UserRole, s)
            self.sessions_list.addItem(item)

    def on_chat_session_clicked(self, item):
        session = item.data(Qt.ItemDataRole.UserRole)
        self.open_chat_tab(session['id'])

    def delete_selected_chat_session(self):
        item = self.sessions_list.currentItem()
        if not item:
            return
        session = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(self, "Delete Chat", f"Are you sure you want to delete '{session['name']}'?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_chat_session(session['id'])
            self.load_chat_sessions()
            
            # Close tab if open
            for i in range(self.central_tabs.count()):
                widget = self.central_tabs.widget(i)
                if isinstance(widget, ChatWidget) and widget.current_session_id == session['id']:
                    self.central_tabs.removeTab(i)
                    widget.deleteLater()
                    break

    def on_calendar_date_changed(self):
        self.current_date_filter = self.calendar.selectedDate().toString("yyyy-MM-dd")
        self.load_history()
        self.refresh_tag_filter()
        
    def reset_date_filter(self):
        self.current_date_filter = None
        # Maybe reset calendar selection visually? 
        # QCalendarWidget always has a selected date, so we can't really "deselect" it easily.
        # But our logic will ignore it.
        self.load_history()
        self.refresh_tag_filter()

    def filter_history_list(self, text):
        for i in range(self.history_list.count()):
            item = self.history_list.item(i)
            record = item.data(Qt.ItemDataRole.UserRole)
            title = record.get('title', '') or ''
            date = record.get('created_at', '') or ''
            
            if not text or text.lower() in title.lower() or text.lower() in date.lower():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def on_favorite_toggled(self, record_id, is_favorite):
        self.db.toggle_favorite(record_id, is_favorite)
        # No need to reload list, button state is already updated locally
        
    def delete_recording(self, record_id):
        reply = QMessageBox.question(self, "Delete Recording", 
                                   "Are you sure you want to delete this recording? This cannot be undone.",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            filename = self.db.delete(record_id)
            
            # Delete file
            if filename:
                try:
                    file_path = os.path.join(os.getcwd(), "recordings", filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"Error deleting file {filename}: {e}")
            
            # Delete from RAG
            if self.rag:
                try:
                    self.rag.delete_document(str(record_id))
                except Exception as e:
                    print(f"Error deleting from RAG: {e}")
            
            self.load_history()
            
            # Close tab if open
            for i in range(self.central_tabs.count()):
                widget = self.central_tabs.widget(i)
                if isinstance(widget, RecordingWidget) and widget.current_record_id == record_id:
                    self.central_tabs.removeTab(i)
                    widget.deleteLater()
                    break

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def import_audio_file(self, config):
        """Import an audio file with the given transcription configuration."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Audio", "", "Audio Files (*.wav *.mp3 *.m4a *.ogg *.flac);;All Files (*)")
        if not file_path:
            return

        try:
            # 1. Copy file to recordings dir
            filename = os.path.basename(file_path)
            dest_path = os.path.join(os.getcwd(), "recordings", filename)
            
            # Handle duplicate filenames
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(filename)
                i = 1
                while os.path.exists(dest_path):
                    new_filename = f"{base}_{i}{ext}"
                    dest_path = os.path.join(os.getcwd(), "recordings", new_filename)
                    i += 1
                filename = os.path.basename(dest_path)

            shutil.copy2(file_path, dest_path)

            # 2. Create DB entry
            record_id = self.db.save(filename, "", 0.0, title=filename)
            
            # 3. Open Recording Tab with config
            rec_widget = self.open_recording_tab(record_id, config)
            
            # 4. Trigger Transcription with config
            if rec_widget and isinstance(rec_widget, RecordingWidget):
                rec_widget.start_transcription_with_config(dest_path, config)

        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import audio: {e}")

    def open_notebooks_list(self):
        # Check if already open
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, NotebooksListWidget):
                self.central_tabs.setCurrentIndex(i)
                return

        nb_list = NotebooksListWidget(self.notebook_db)
        nb_list.notebook_opened.connect(self.open_notebook)
        nb_list.chat_requested.connect(self.open_notebook_chat)
        
        index = self.central_tabs.addTab(nb_list, "Libretas")
        self.central_tabs.setCurrentIndex(index)

    def open_notebook(self, notebook_id, name):
        # Check if already open
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, NotebookWidget) and widget.notebook_id == notebook_id:
                self.central_tabs.setCurrentIndex(i)
                return

        nb_widget = NotebookWidget(self.notebook_db, notebook_id, name, self.recorder)
        nb_widget.chat_requested.connect(self.open_notebook_chat)
        
        index = self.central_tabs.addTab(nb_widget, f"📓 {name}")
        self.central_tabs.setCurrentIndex(index)

    def open_notebook_chat(self, notebook_id, notebook_name):
        # Check if already open
        # We can try to find a chat with this notebook as context
        # But for now, let's just open a new one or rely on user to manage
        
        self.open_chat_tab(initial_contexts=[{"type": "notebook", "value": notebook_id, "label": notebook_name}])

    def open_maintenance_tab(self):
        # Check if already open
        for i in range(self.central_tabs.count()):
            widget = self.central_tabs.widget(i)
            if isinstance(widget, MaintenanceWidget):
                self.central_tabs.setCurrentIndex(i)
                return

        maint_widget = MaintenanceWidget(self.db)
        maint_widget.batch_processing_requested.connect(self.open_batch_process_tab)
        
        index = self.central_tabs.addTab(maint_widget, "Maintenance")
        self.central_tabs.setCurrentIndex(index)

