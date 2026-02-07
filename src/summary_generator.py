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

from typing import List, Tuple, Optional
from PyQt6.QtCore import QThread, pyqtSignal, QSettings
from src.database import DBManager
from src.ai_provider import get_ai_provider, validate_ai_provider_config


class SummaryGenerator(QThread):
    """
    Generates summaries for days and weeks that have content but no summary.
    
    Signals:
        progress: Emitted with (current, total) for progress updates.
        item_completed: Emitted with (type, date, summary) when an item is done.
        finished: Emitted with (daily_count, weekly_count) when all done.
        error: Emitted with error message if something fails.
    """
    
    progress = pyqtSignal(int, int)  # current, total
    item_completed = pyqtSignal(str, str, str)  # type ("daily"/"weekly"), date, summary
    finished = pyqtSignal(int, int)  # daily_count, weekly_count
    error = pyqtSignal(str)
    
    def __init__(self, generate_daily: bool = True, generate_weekly: bool = True, 
                 tags_filter: Optional[str] = None, parent=None):
        """
        Initialize the summary generator.
        
        Args:
            generate_daily: Whether to generate daily summaries.
            generate_weekly: Whether to generate weekly summaries.
            tags_filter: Optional tags filter (comma-separated).
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.generate_daily = generate_daily
        self.generate_weekly = generate_weekly
        self.tags_filter = tags_filter
        self.db = DBManager()
        self._cancelled = False
        
    def cancel(self):
        """Request cancellation of the generation process."""
        self._cancelled = True
        
    def run(self):
        """Run the summary generation process."""
        try:
            settings = QSettings("Hectronic", "Secretario")
            
            # Validate AI provider
            is_valid, error_msg = validate_ai_provider_config(settings)
            if not is_valid:
                self.error.emit(error_msg)
                return
                
            provider = get_ai_provider(settings)
            
            # Get pending dates/weeks
            pending_dates = []
            pending_weeks = []
            
            if self.generate_daily:
                pending_dates = self.db.get_dates_without_summary(self.tags_filter)
                
            if self.generate_weekly:
                pending_weeks = self.db.get_weeks_without_summary(self.tags_filter)
                
            total = len(pending_dates) + len(pending_weeks)
            if total == 0:
                self.finished.emit(0, 0)
                return
                
            current = 0
            daily_count = 0
            weekly_count = 0
            
            # Load prompts from settings
            default_daily_prompt = """Please provide a concise summary of all recordings from this day.
Highlight key points, decisions made, and action items if any.
Keep it brief but comprehensive.

Day's recordings:
{text}"""

            default_weekly_prompt = """Please provide a comprehensive summary of the following recordings from this week.
Group the summary by topic or day if relevant.
Highlight key achievements, decisions, and action items.

Recordings Content:
{text}"""
            
            daily_prompt_template = settings.value("prompt_daily_summary", default_daily_prompt)
            weekly_prompt_template = settings.value("prompt_weekly_summary", default_weekly_prompt)
            
            # Process daily summaries
            for date in pending_dates:
                if self._cancelled:
                    break
                    
                current += 1
                self.progress.emit(current, total)
                
                # Fetch recordings for the day
                tags_list = self.tags_filter.split(',') if self.tags_filter else None
                recordings = self.db.fetch_by_dates([date], tags_list)
                
                if not recordings:
                    continue
                    
                # Prepare text
                full_text = self._prepare_recordings_text(recordings)
                if not full_text.strip():
                    continue
                    
                # Generate summary
                prompt = daily_prompt_template.replace("{text}", full_text)
                summary = provider.generate_content(prompt)
                
                # Save to database
                self.db.save_daily_summary(date, summary, self.tags_filter)
                daily_count += 1
                self.item_completed.emit("daily", date, summary)
                
            # Process weekly summaries
            for week_start in pending_weeks:
                if self._cancelled:
                    break
                    
                current += 1
                self.progress.emit(current, total)
                
                # Fetch recordings for the week (7 days starting from Monday)
                week_dates = self._get_week_dates(week_start)
                tags_list = self.tags_filter.split(',') if self.tags_filter else None
                recordings = self.db.fetch_by_dates(week_dates, tags_list)
                
                if not recordings:
                    continue
                    
                # Prepare text
                full_text = self._prepare_recordings_text(recordings)
                if not full_text.strip():
                    continue
                    
                # Generate summary
                prompt = weekly_prompt_template.replace("{text}", full_text)
                summary = provider.generate_content(prompt)
                
                # Save to database
                self.db.save_weekly_summary(week_start, summary, self.tags_filter)
                weekly_count += 1
                self.item_completed.emit("weekly", week_start, summary)
                
            self.finished.emit(daily_count, weekly_count)
            
        except Exception as e:
            self.error.emit(str(e))
            
    def _prepare_recordings_text(self, recordings: List[dict]) -> str:
        """Prepare the text content from a list of recordings."""
        full_text = ""
        for rec in recordings:
            full_text += f"\n\n--- Recording: {rec.get('title', 'Untitled')} ({rec.get('created_at', '')}) ---\n"
            full_text += rec.get('transcription', '') or ""
        return full_text
        
    def _get_week_dates(self, week_start: str) -> List[str]:
        """Get list of date strings for a week starting from week_start (Monday)."""
        from datetime import datetime, timedelta
        
        start = datetime.strptime(week_start, "%Y-%m-%d")
        return [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]


def get_pending_summary_counts(tags_filter: Optional[str] = None) -> Tuple[int, int]:
    """
    Get the count of days and weeks that need summaries.
    
    Args:
        tags_filter: Optional tags filter.
        
    Returns:
        Tuple of (pending_daily_count, pending_weekly_count).
    """
    db = DBManager()
    pending_dates = db.get_dates_without_summary(tags_filter)
    pending_weeks = db.get_weeks_without_summary(tags_filter)
    return len(pending_dates), len(pending_weeks)
