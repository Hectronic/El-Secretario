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

"""RAG runtime setup and startup summary scheduling for the main window."""

import logging
import os
from datetime import date, timedelta

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QMessageBox


class RuntimeStartupCoordinator:
    """Own non-layout runtime setup performed by the main-window shell."""

    def __init__(self, window):
        self.window = window

    @staticmethod
    def to_env_bool(value) -> str:
        return "1" if bool(value) else "0"

    def apply_rag_runtime_env(self, rag_config):
        os.environ["EL_SECRETARIO_CHROMA_SAFE_DELETE"] = self.to_env_bool(
            rag_config.get("safe_delete_mode", True)
        )
        os.environ["EL_SECRETARIO_RAG_SUBPROCESS_UPSERT"] = self.to_env_bool(
            rag_config.get("subprocess_upsert_mode", True)
        )
        os.environ["EL_SECRETARIO_RAG_SUBPROCESS_QUERY"] = self.to_env_bool(
            rag_config.get("subprocess_query_mode", True)
        )

    def initialize_rag_from_settings(self):
        settings = QSettings("Hectronic", "Secretario")
        self.build_rag_engine(
            {
                "enabled": settings.value("rag_enabled", True, type=bool),
                "persist_directory": settings.value("rag_persist_directory", "chroma_db"),
                "safe_delete_mode": settings.value("rag_safe_delete_mode", True, type=bool),
                "subprocess_upsert_mode": settings.value("rag_subprocess_upsert_mode", True, type=bool),
                "subprocess_query_mode": settings.value("rag_subprocess_query_mode", True, type=bool),
            },
            reason="startup",
        )

    def propagate_rag_engine_to_open_tabs(self):
        for index in range(self.window.central_tabs.count()):
            widget = self.window.central_tabs.widget(index)
            if hasattr(widget, "rag"):
                try:
                    widget.rag = self.window.rag
                except Exception:
                    logging.exception("Failed to propagate RAG engine to tab %s", type(widget).__name__)

    def build_rag_engine(self, rag_config, reason="runtime"):
        window = self.window
        self.apply_rag_runtime_env(rag_config)
        if not rag_config.get("enabled", True):
            window.rag = None
            window.summary_task_queue.set_rag_engine(None)
            self.propagate_rag_engine_to_open_tabs()
            window.handle_status_message("RAG disabled from settings.")
            logging.info("RAG disabled (%s).", reason)
            return

        persist_dir = rag_config.get("persist_directory") or "chroma_db"
        try:
            from src.rag_engine import RAGEngine

            window.rag = RAGEngine(persist_directory=persist_dir)
            window.summary_task_queue.set_rag_engine(window.rag)
            self.propagate_rag_engine_to_open_tabs()
            window.handle_status_message(f"RAG ready ({reason}).")
            logging.info("RAG initialized (%s) with persist_directory=%s", reason, persist_dir)
        except Exception as error:
            window.rag = None
            window.summary_task_queue.set_rag_engine(None)
            self.propagate_rag_engine_to_open_tabs()
            logging.exception("Failed to initialize RAG (%s).", reason)
            if str(reason).lower() == "startup":
                window.handle_status_message(f"RAG unavailable on startup: {error}")
            else:
                QMessageBox.warning(window, "RAG Error", f"Failed to initialize RAG: {error}")

    def log_user_settings_snapshot(self, context: str):
        settings = QSettings("Hectronic", "Secretario")
        snapshot = {}
        for key in sorted(settings.allKeys()):
            value = settings.value(key)
            key_lower = str(key).lower()
            snapshot[key] = (
                "***"
                if any(token in key_lower for token in ("token", "password", "secret", "apikey", "api_key"))
                else value
            )
        logging.info("User settings snapshot [%s]: %s", context, snapshot)

    def enqueue_missing_previous_week_summary_if_enabled(self):
        window = self.window
        settings = QSettings("Hectronic", "Secretario")
        if not settings.value("startup_enqueue_last_weekly_summary", False, type=bool):
            return

        today = date.today()
        current_week_monday = today - timedelta(days=today.weekday())
        previous_week_monday = current_week_monday - timedelta(days=7)
        previous_week_sunday = previous_week_monday + timedelta(days=6)
        week_sunday_str = previous_week_sunday.isoformat()

        if window.db.get_weekly_summary(week_sunday_str, tags_filter=None):
            return

        records = window.db.fetch_by_date_range(
            previous_week_monday.isoformat(),
            week_sunday_str,
            tags=None,
            favorites_only=False,
        )
        if not records:
            return

        full_text = ""
        for record in records:
            title = record.get("title") or "Untitled"
            created_at = record.get("created_at") or ""
            composed = window.db.compose_ai_text(record.get("transcription"), record.get("recording_notes"))
            if composed.strip():
                full_text += f"\n\n--- Recording: {title} ({created_at}) ---\n{composed}"

        if full_text.strip():
            window.summary_task_queue.enqueue_weekly_summary(
                week_sunday_str, full_text, "", source="startup"
            )

    def enqueue_missing_previous_daily_summary_if_enabled(self):
        window = self.window
        settings = QSettings("Hectronic", "Secretario")
        if not settings.value("startup_enqueue_previous_daily_summary", False, type=bool):
            return

        target_day = window.db.get_latest_recording_day_without_daily_summary(
            date.today().isoformat(), tags_filter=None
        )
        if target_day:
            window.summary_task_queue.enqueue_daily_summary(
                {"date": target_day, "tags_filter": "", "source": "startup"}
            )
