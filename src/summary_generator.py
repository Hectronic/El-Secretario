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
from datetime import datetime
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
    item_completed = pyqtSignal(str, str, str)  # type ("daily"/"weekly"/"recording"), date/title, summary
    finished = pyqtSignal(int, int, int)  # local_recordings_count, daily_count, weekly_count
    error = pyqtSignal(str)
    
    def __init__(self, generate_daily: bool = True, generate_weekly: bool = True, 
                 generate_recordings: bool = True,
                 tags_filter: Optional[str] = None, 
                 exclude_today: bool = True,
                 exclude_current_week: bool = True,
                 specific_dates: Optional[List[str]] = None,
                 parent=None):
        """
        Initialize the summary generator.
        
        Args:
            generate_daily: Whether to generate daily summaries.
            generate_weekly: Whether to generate weekly summaries.
            generate_recordings: Whether to generate summaries for individual recordings.
            tags_filter: Optional tags filter (comma-separated).
            exclude_today: Whether to exclude today from daily summaries.
            exclude_current_week: Whether to exclude current week from weekly summaries.
            specific_dates: Optional list of specific dates (YYYY-MM-DD) to process.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.generate_daily = generate_daily
        self.generate_weekly = generate_weekly
        self.generate_recordings = generate_recordings
        self.tags_filter = tags_filter
        self.exclude_today = exclude_today
        self.exclude_current_week = exclude_current_week
        self.specific_dates = specific_dates
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
            
            
        except Exception as e:
            self.error.emit(str(e))
        try:
            settings = QSettings("Hectronic", "Secretario")
            
            # Validate AI provider
            is_valid, error_msg = validate_ai_provider_config(settings)
            if not is_valid:
                self.error.emit(error_msg)
                return
                
            provider = get_ai_provider(settings)
            
            # 1. Identify all dates that need processing
            # We need dates that:
            # a) Have pending recording summaries (if generate_recordings is True)
            # b) Have pending daily summary (if generate_daily is True)
            
            dates_to_process = set()
            
            if self.specific_dates:
                 # If specific dates are provided, use them directly
                 for date in self.specific_dates:
                     dates_to_process.add(date)
            elif self.generate_daily or self.generate_recordings:
                all_dates = self.db.get_dates_with_content()
                for date in all_dates:
                    # Check exclusions
                    if self.exclude_today and date == datetime.now().strftime("%Y-%m-%d"):
                        continue
                    dates_to_process.add(date)
            
            # Sort dates Newest -> Oldest
            sorted_dates = sorted(list(dates_to_process), reverse=True)
            
            # Identify weeks to process
            weeks_to_process = []
            if self.generate_weekly:
                pending_weeks = self.db.get_weeks_without_summary(self.tags_filter, self.exclude_current_week)
                weeks_to_process = sorted(pending_weeks, reverse=True)
                
            total_steps = len(sorted_dates) + len(weeks_to_process)
            if total_steps == 0:
                self.finished.emit(0, 0, 0)
                return
                
            current_step = 0
            daily_count = 0
            weekly_count = 0
            recordings_count = 0 
            
            # Load prompts
            default_daily_prompt = """Please provide a concise summary of the day based on the following meeting summaries.
Highlight key points, decisions made, and action items if any.

Meeting Summaries:
{text}"""

            default_weekly_prompt = """Please provide a comprehensive summary of the following recordings from this week.
Group the summary by topic or day if relevant.
Highlight key achievements, decisions, and action items.

Recordings Content:
{text}"""

            default_recording_prompt = """Please provide a concise and structured summary of the following transcription.
Highlight key points, decisions made, and action items if any.

Transcription:
{text}"""
            
            daily_prompt_template = settings.value("prompt_daily_summary_from_summaries", default_daily_prompt)
            # Fallback if the new prompt key doesn't exist yet, maybe use the old one but it might expect raw text?
            # actually, the old prompt expects {text}, so it might work if we verify wording.
            # But let's stick to a specific one for "from summaries".
            
            weekly_prompt_template = settings.value("prompt_weekly_summary", default_weekly_prompt)
            recording_prompt_template = settings.value("prompt_summary", default_recording_prompt)
            
            # 2. Process Dates (Newest -> Oldest)
            for date in sorted_dates:
                if self._cancelled:
                    break
                    
                current_step += 1
                self.progress.emit(current_step, total_steps)
                
                # Fetch recordings for the day
                tags_list = self.tags_filter.split(',') if self.tags_filter else None
                recordings = self.db.fetch_by_dates([date], tags_list)
                
                if not recordings:
                    continue
                
                # Sort recordings Newest -> Oldest (created_at desc) - fetch_by_dates already does this
                
                day_generated_summaries = [] # To store summaries we might use for daily summary
                day_has_pending_daily = False
                
                # Check if daily summary is missing
                # If specific_dates is active, we force generation (treat as missing)
                existing_daily = self.db.get_daily_summary(date, self.tags_filter)
                if not existing_daily or (self.specific_dates and date in self.specific_dates):
                    day_has_pending_daily = True
                
                # Process recordings for this day
                processed_rec_for_day = False
                for rec in recordings:
                    if self._cancelled:
                        break
                        
                    # Check if recording needs summary
                    param_summary = rec.get('summary')
                    
                    rec_summary = None
                    if not param_summary or not param_summary.strip():
                        if self.generate_recordings:
                            text = rec.get('transcription', '')
                            if text and text.strip():
                                prompt = recording_prompt_template.replace("{text}", text)
                                rec_summary = provider.generate_content(prompt)
                                self.db.update_ai_content(rec['id'], summary=rec_summary)
                                recordings_count += 1
                                self.item_completed.emit("recording", rec.get('title', 'Untitled'), rec_summary)
                                processed_rec_for_day = True
                                
                    if not rec_summary and param_summary:
                        rec_summary = param_summary
                    
                    if rec_summary:
                        day_generated_summaries.append(f"Title: {rec.get('title', 'Untitled')}\nSummary: {rec_summary}")
                
                # Generate Daily Summary if needed
                # We generate if:
                # 1. generate_daily is True AND
                # 2. (Daily summary is missing OR We just generated new recording summaries which might update the day)
                # Actually, strictly following "Daily summary uses summaries of each meeting", 
                # if we just generated a recording summary, the old daily summary is stale.
                # So we should regenerate if processed_rec_for_day is True OR day_has_pending_daily.
                
                if self.generate_daily and (day_has_pending_daily or processed_rec_for_day) and day_generated_summaries:
                    full_text = "\n\n".join(day_generated_summaries)
                    prompt = daily_prompt_template.replace("{text}", full_text)
                    summary = provider.generate_content(prompt)
                    
                    self.db.save_daily_summary(date, summary, self.tags_filter)
                    daily_count += 1
                    self.item_completed.emit("daily", date, summary)

            # 3. Process Weeks (Newest -> Oldest)
            for week_start in weeks_to_process:
                if self._cancelled:
                    break
                    
                current_step += 1
                self.progress.emit(current_step, total_steps)
                
                week_dates = self._get_week_dates(week_start)
                tags_list = self.tags_filter.split(',') if self.tags_filter else None
                recordings = self.db.fetch_by_dates(week_dates, tags_list)
                
                if not recordings:
                    continue
                    
                full_text = self._prepare_recordings_text(recordings)
                if not full_text.strip():
                    continue
                    
                prompt = weekly_prompt_template.replace("{text}", full_text)
                summary = provider.generate_content(prompt)
                
                self.db.save_weekly_summary(week_start, summary, self.tags_filter)
                weekly_count += 1
                self.item_completed.emit("weekly", week_start, summary)
                
            self.finished.emit(recordings_count, daily_count, weekly_count)
            
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
