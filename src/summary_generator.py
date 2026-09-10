# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Qt adapter for the focused summary-generation application service."""

import logging
from typing import List, Optional, Tuple

from PyQt6.QtCore import QSettings, QThread, pyqtSignal

from src.ai_provider import (
    generate_content_with_retry,
    get_ai_provider,
    validate_ai_provider_config,
)
from src.app.summaries import SummaryGenerationOptions, SummaryGenerationService
from src.database import DBManager


class SummaryGenerator(QThread):
    """Run summary generation in a Qt thread while forwarding service outcomes."""

    progress = pyqtSignal(int, int)
    item_completed = pyqtSignal(str, str, str)
    recording_summary_completed = pyqtSignal(int, str)
    all_tasks_finished = pyqtSignal(int, int, int)
    error = pyqtSignal(str)
    status_update = pyqtSignal(str)
    retry_wait = pyqtSignal(float, int, int, str)

    def __init__(
        self,
        generate_daily: bool = True,
        generate_weekly: bool = True,
        generate_recordings: bool = True,
        tags_filter: Optional[str] = None,
        exclude_today: bool = True,
        exclude_current_week: bool = True,
        specific_dates: Optional[List[str]] = None,
        parent=None,
        persistence=None,
    ):
        super().__init__(parent)
        self.options = SummaryGenerationOptions(
            generate_daily=generate_daily,
            generate_weekly=generate_weekly,
            generate_recordings=generate_recordings,
            tags_filter=tags_filter,
            exclude_today=exclude_today,
            exclude_current_week=exclude_current_week,
            specific_dates=specific_dates,
        )
        self.db = persistence if persistence is not None else DBManager()
        self._cancelled = False

    @property
    def generate_daily(self):
        return self.options.generate_daily

    @property
    def generate_weekly(self):
        return self.options.generate_weekly

    @property
    def generate_recordings(self):
        return self.options.generate_recordings

    @property
    def tags_filter(self):
        return self.options.tags_filter

    @property
    def exclude_today(self):
        return self.options.exclude_today

    @property
    def exclude_current_week(self):
        return self.options.exclude_current_week

    @property
    def specific_dates(self):
        return self.options.specific_dates

    def cancel(self):
        """Request cancellation; the service checks before each work item."""
        self._cancelled = True

    def run(self):
        """Validate the provider and relay service callbacks through Qt signals."""
        try:
            settings = QSettings("Hectronic", "Secretario")
            valid, error_message = validate_ai_provider_config(settings)
            if not valid:
                self.error.emit(error_message)
                return
            if self._cancelled:
                self.all_tasks_finished.emit(0, 0, 0)
                return

            service = SummaryGenerationService(
                self.db,
                settings,
                get_ai_provider(settings),
                generate_content_with_retry,
            )
            counts = service.generate(
                self.options,
                is_cancelled=lambda: self._cancelled,
                on_progress=self.progress.emit,
                on_item_completed=self.item_completed.emit,
                on_recording_summary_completed=self.recording_summary_completed.emit,
                on_retry=self._emit_retry_wait,
            )
            self.all_tasks_finished.emit(*counts)
        except Exception as error:
            logging.error("SummaryGenerator error: %s", error, exc_info=True)
            self.error.emit(str(error))

    def _prepare_recordings_text(self, recordings: List[dict]) -> str:
        """Compatibility delegate for callers of the previous private helper."""
        service = SummaryGenerationService(self.db, None, None, None)
        return service.prepare_recordings_text(recordings)

    def _emit_retry_wait(self, task_name, target, delay, attempt, total_attempts, error_text):
        self.status_update.emit(
            f"{task_name} ({target}): waiting {float(delay):.1f}s before retry "
            f"({int(attempt) + 1}/{int(total_attempts)})"
        )
        self.retry_wait.emit(float(delay), int(attempt), int(total_attempts), str(error_text))

    @staticmethod
    def _get_week_dates(week_end: str) -> List[str]:
        """Compatibility delegate for weekly date expansion."""
        return SummaryGenerationService.week_dates(week_end)


def get_pending_summary_counts(tags_filter: Optional[str] = None) -> Tuple[int, int]:
    """Return pending daily and weekly counts through the compatible DB facade."""
    db = DBManager()
    return len(db.get_dates_without_summary(tags_filter)), len(db.get_weeks_without_summary(tags_filter))
