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
# along with this program.  See <https://www.gnu.org/licenses/>.

from typing import List, Tuple, Optional
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal, QSettings
from src.database import DBManager
from src.ai_provider import get_ai_provider, validate_ai_provider_config, generate_content_with_retry
import logging


class SummaryGenerator(QThread):
    """
    Generates summaries for days and weeks that have content but no summary.
    
    Signals:
        progress: Emitted with (current, total) for progress updates.
        item_completed: Emitted with (type, date, summary) when an item is done.
        all_tasks_finished: Emitted with (recordings_count, daily_count, weekly_count) when all done.
        error: Emitted with error message if something fails.
    """
    
    progress = pyqtSignal(int, int)  # current, total
    item_completed = pyqtSignal(str, str, str)  # type ("daily"/"weekly"/"recording"), date/title, summary
    recording_summary_completed = pyqtSignal(int, str)  # record_id, title
    all_tasks_finished = pyqtSignal(int, int, int)  # local_recordings_count, daily_count, weekly_count
    error = pyqtSignal(str)
    status_update = pyqtSignal(str)
    retry_wait = pyqtSignal(float, int, int, str)  # delay, attempt, total_attempts, error
    
    def __init__(self, generate_daily: bool = True, generate_weekly: bool = True, 
                 generate_recordings: bool = True,
                 tags_filter: Optional[str] = None, 
                 exclude_today: bool = True,
                 exclude_current_week: bool = True,
                 specific_dates: Optional[List[str]] = None,
                 parent=None):
        """
        Initialize the summary generator.
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
            if self._cancelled:
                self.all_tasks_finished.emit(0, 0, 0)
                return
            
            # 1. Identify all dates that need processing
            dates_to_process = set()
            
            if self.specific_dates:
                 for date in self.specific_dates:
                     dates_to_process.add(date)
            elif self.generate_daily or self.generate_recordings:
                all_dates = self.db.get_dates_with_content()
                for date in all_dates:
                    if self.exclude_today and date == datetime.now().strftime("%Y-%m-%d") and not self.generate_recordings:
                        continue
                    dates_to_process.add(date)
            
            sorted_dates = sorted(list(dates_to_process), reverse=True)
            
            weeks_to_process = []
            if self.generate_weekly:
                pending_weeks = self.db.get_weeks_without_summary(self.tags_filter, self.exclude_current_week)
                weeks_to_process = sorted(pending_weeks, reverse=True)
                
            total_steps = len(sorted_dates) + len(weeks_to_process)
            if total_steps == 0:
                self.all_tasks_finished.emit(0, 0, 0)
                return
                
            current_step = 0
            daily_count = 0
            weekly_count = 0
            recordings_count = 0 
            
            # Default prompts
            default_daily_prompt = """As an expert assistant, provide a concise and structured daily summary based on the following recording summaries from today.
Group key information by topic, highlight important decisions, and list any pending action items.
The summary MUST be written in {language}.

Meeting Summaries:
{text}"""

            default_weekly_prompt = """As an expert assistant, provide a comprehensive and professional weekly summary based on the following recording content from this week.
Organize the summary by topic or day, highlighting key achievements, strategic decisions, and future action items.
The summary MUST be written in {language}.

Recordings Content:
{text}"""

            default_recording_prompt = """Please provide a concise and structured summary of the following transcription.
Highlight key points, decisions made, and action items if any.
The summary MUST be written in {language}.

Transcription:
{text}"""
            
            daily_prompt_template = settings.value("prompt_daily_summary", default_daily_prompt)
            weekly_prompt_template = settings.value("prompt_weekly_summary", default_weekly_prompt)
            recording_prompt_template = settings.value("prompt_summary", default_recording_prompt)
            
            language = settings.value("system_language", "Spanish")
            
            # 2. Process Dates
            for date in sorted_dates:
                if self._cancelled: break
                    
                current_step += 1
                self.progress.emit(current_step, total_steps)
                
                tags_list = self.tags_filter.split(',') if self.tags_filter else None
                recordings = self.db.fetch_by_dates([date], tags_list)
                if not recordings: continue
                
                day_generated_summaries = [] 
                day_has_pending_daily = False
                
                existing_daily = self.db.get_daily_summary(date, self.tags_filter)
                if not existing_daily or (self.specific_dates and date in self.specific_dates):
                    day_has_pending_daily = True
                
                processed_rec_for_day = False
                for rec in recordings:
                    if self._cancelled: break
                        
                    param_summary = rec.get('summary')
                    rec_summary = None
                    
                    if not param_summary or not param_summary.strip():
                        if self.generate_recordings:
                            text = self.db.compose_ai_text(rec.get('transcription', ''), rec.get('recording_notes', ''))
                            if text and text.strip():
                                # Summary Generation
                                prompt = recording_prompt_template.replace("{text}", text)
                                if "{language}" in prompt: prompt = prompt.replace("{language}", language)
                                
                                logging.info(f"SummaryGenerator: Requesting summary for recording {rec['id']}")
                                rec_summary = generate_content_with_retry(
                                    provider=provider,
                                    settings=settings,
                                    prompt=prompt,
                                    operation_name=f"SummaryGenerator.recording_summary[{rec['id']}]",
                                    on_retry=lambda d, a, t, e, rid=rec.get("id"): self._emit_retry_wait("recording_summary", rid, d, a, t, e),
                                )
                                self.db.update_ai_content(rec['id'], summary=rec_summary)
                                recordings_count += 1
                                self.item_completed.emit("recording", rec.get('title', 'Untitled'), rec_summary)
                                self.recording_summary_completed.emit(int(rec['id']), rec.get('title', 'Untitled'))
                                processed_rec_for_day = True
                                
                    if not rec_summary and param_summary:
                        rec_summary = param_summary
                    
                    if rec_summary:
                        day_generated_summaries.append(f"Title: {rec.get('title', 'Untitled')}\nSummary: {rec_summary}")
                
                is_today = (date == datetime.now().strftime("%Y-%m-%d"))
                skip_daily_today = (self.exclude_today and is_today)
                
                if self.generate_daily and (day_has_pending_daily or processed_rec_for_day) and day_generated_summaries and not skip_daily_today:
                    full_text = "\n\n".join(day_generated_summaries)
                    prompt = daily_prompt_template.replace("{text}", full_text)
                    if "{language}" in prompt: prompt = prompt.replace("{language}", language)
                    
                    logging.info(f"SummaryGenerator: Requesting daily summary for {date}")
                    summary = generate_content_with_retry(
                        provider=provider,
                        settings=settings,
                        prompt=prompt,
                        operation_name=f"SummaryGenerator.daily_summary[{date}]",
                        on_retry=lambda d, a, t, e, target=date: self._emit_retry_wait("daily_summary", target, d, a, t, e),
                    )
                    self.db.save_daily_summary(date, summary, self.tags_filter)
                    daily_count += 1
                    self.item_completed.emit("daily", date, summary)

            # 3. Process Weeks
            for week_date in weeks_to_process:
                if self._cancelled: break
                current_step += 1
                self.progress.emit(current_step, total_steps)
                
                week_dates = self._get_week_dates(week_date)
                tags_list = self.tags_filter.split(',') if self.tags_filter else None
                recordings = self.db.fetch_by_dates(week_dates, tags_list)
                if not recordings: continue
                    
                full_text = self._prepare_recordings_text(recordings)
                if not full_text.strip(): continue
                    
                prompt = weekly_prompt_template.replace("{text}", full_text)
                if "{language}" in prompt: prompt = prompt.replace("{language}", language)
                
                logging.info(f"SummaryGenerator: Requesting weekly summary for {week_date}")
                summary = generate_content_with_retry(
                    provider=provider,
                    settings=settings,
                    prompt=prompt,
                    operation_name=f"SummaryGenerator.weekly_summary[{week_date}]",
                    on_retry=lambda d, a, t, e, target=week_date: self._emit_retry_wait("weekly_summary", target, d, a, t, e),
                )
                self.db.save_weekly_summary(week_date, summary, self.tags_filter)
                weekly_count += 1
                self.item_completed.emit("weekly", week_date, summary)
                
            self.all_tasks_finished.emit(recordings_count, daily_count, weekly_count)
            
        except Exception as e:
            logging.error(f"SummaryGenerator error: {e}", exc_info=True)
            self.error.emit(str(e))
            
    def _prepare_recordings_text(self, recordings: List[dict]) -> str:
        """Prepare the text content from a list of recordings."""
        full_text = ""
        for rec in recordings:
            full_text += f"\n\n--- Recording: {rec.get('title', 'Untitled')} ({rec.get('created_at', '')}) ---\n"
            full_text += self.db.compose_ai_text(rec.get('transcription', ''), rec.get('recording_notes', ''))
        return full_text

    def _emit_retry_wait(self, task_name, target, delay, attempt, total_attempts, error_text):
        self.status_update.emit(
            f"{task_name} ({target}): waiting {float(delay):.1f}s before retry ({int(attempt) + 1}/{int(total_attempts)})"
        )
        self.retry_wait.emit(float(delay), int(attempt), int(total_attempts), str(error_text))
        
    def _get_week_dates(self, week_end: str) -> List[str]:
        """Get list of date strings for a week ending on week_end (Sunday)."""
        from datetime import datetime, timedelta
        end = datetime.strptime(week_end, "%Y-%m-%d")
        return [(end - timedelta(days=6-i)).strftime("%Y-%m-%d") for i in range(7)]


def get_pending_summary_counts(tags_filter: Optional[str] = None) -> Tuple[int, int]:
    """
    Get the count of days and weeks that need summaries.
    """
    db = DBManager()
    pending_dates = db.get_dates_without_summary(tags_filter)
    pending_weeks = db.get_weeks_without_summary(tags_filter)
    return len(pending_dates), len(pending_weeks)
