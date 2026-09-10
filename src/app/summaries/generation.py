"""Non-Qt summary generation workflow with explicit observable callbacks."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Iterable, Optional


DEFAULT_DAILY_PROMPT = """As an expert assistant, provide a concise and structured daily summary based on the following recording summaries from today.
Group key information by topic, highlight important decisions, and list any pending action items.
The summary MUST be written in {language}.

Meeting Summaries:
{text}"""

DEFAULT_WEEKLY_PROMPT = """As an expert assistant, provide a comprehensive and professional weekly summary based on the following recording content from this week.
Organize the summary by topic or day, highlighting key achievements, strategic decisions, and future action items.
The summary MUST be written in {language}.

Recordings Content:
{text}"""

DEFAULT_RECORDING_PROMPT = """Please provide a concise and structured summary of the following transcription.
Highlight key points, decisions made, and action items if any.
The summary MUST be written in {language}.

Transcription:
{text}"""


@dataclass(frozen=True)
class SummaryGenerationOptions:
    """Work selection requested by the Qt adapter or a future non-Qt caller."""

    generate_daily: bool = True
    generate_weekly: bool = True
    generate_recordings: bool = True
    tags_filter: Optional[str] = None
    exclude_today: bool = True
    exclude_current_week: bool = True
    specific_dates: Optional[list[str]] = None


class SummaryGenerationService:
    """Generate and persist summaries without depending on Qt threads or signals."""

    def __init__(self, persistence, settings, provider, generate_content, *, now=datetime.now):
        self.db = persistence
        self.settings = settings
        self.provider = provider
        self.generate_content = generate_content
        self.now = now

    def generate(
        self,
        options: SummaryGenerationOptions,
        *,
        is_cancelled: Callable[[], bool],
        on_progress: Callable[[int, int], None],
        on_item_completed: Callable[[str, str, str], None],
        on_recording_summary_completed: Callable[[int, str], None],
        on_retry: Callable[[str, str | int, float, int, int, str], None],
    ) -> tuple[int, int, int]:
        """Run requested work and return recording, daily, weekly completion counts."""
        dates = self._dates_to_process(options)
        weeks = self._weeks_to_process(options)
        total_steps = len(dates) + len(weeks)
        if not total_steps or is_cancelled():
            return 0, 0, 0

        prompts = self._prompts()
        recordings_count = daily_count = weekly_count = current_step = 0
        tags = options.tags_filter.split(",") if options.tags_filter else None

        for date in dates:
            if is_cancelled():
                break
            current_step += 1
            on_progress(current_step, total_steps)
            recordings_count, generated, processed = self._process_date(
                date,
                options,
                prompts,
                tags,
                recordings_count,
                is_cancelled,
                on_item_completed,
                on_recording_summary_completed,
                on_retry,
            )
            if self._should_generate_daily(date, options, generated, processed):
                summary = self._generate(
                    "daily_summary", date, prompts["daily"].replace("{text}", "\n\n".join(generated))
                    .replace("{language}", prompts["language"]), on_retry,
                )
                self.db.save_daily_summary(date, summary, options.tags_filter)
                daily_count += 1
                on_item_completed("daily", date, summary)

        for week_date in weeks:
            if is_cancelled():
                break
            current_step += 1
            on_progress(current_step, total_steps)
            recordings = self.db.fetch_by_dates(self.week_dates(week_date), tags)
            full_text = self.prepare_recordings_text(recordings)
            if not full_text.strip():
                continue
            summary = self._generate(
                "weekly_summary", week_date,
                prompts["weekly"].replace("{text}", full_text).replace("{language}", prompts["language"]),
                on_retry,
            )
            self.db.save_weekly_summary(week_date, summary, options.tags_filter)
            weekly_count += 1
            on_item_completed("weekly", week_date, summary)

        return recordings_count, daily_count, weekly_count

    def _dates_to_process(self, options: SummaryGenerationOptions) -> list[str]:
        if options.specific_dates:
            return sorted(set(options.specific_dates), reverse=True)
        if not (options.generate_daily or options.generate_recordings):
            return []
        today = self.now().strftime("%Y-%m-%d")
        return sorted(
            {
                date
                for date in self.db.get_dates_with_content()
                if not (options.exclude_today and date == today and not options.generate_recordings)
            },
            reverse=True,
        )

    def _weeks_to_process(self, options: SummaryGenerationOptions) -> list[str]:
        if not options.generate_weekly:
            return []
        return sorted(
            self.db.get_weeks_without_summary(options.tags_filter, options.exclude_current_week),
            reverse=True,
        )

    def _prompts(self) -> dict[str, str]:
        return {
            "daily": self.settings.value("prompt_daily_summary", DEFAULT_DAILY_PROMPT),
            "weekly": self.settings.value("prompt_weekly_summary", DEFAULT_WEEKLY_PROMPT),
            "recording": self.settings.value("prompt_summary", DEFAULT_RECORDING_PROMPT),
            "language": self.settings.value("system_language", "Spanish"),
        }

    def _process_date(
        self, date, options, prompts, tags, recordings_count, is_cancelled,
        on_item_completed, on_recording_summary_completed, on_retry,
    ):
        recordings = self.db.fetch_by_dates([date], tags)
        if not recordings:
            return recordings_count, [], False
        generated = []
        processed = False
        for record in recordings:
            if is_cancelled():
                break
            summary = record.get("summary") or ""
            if not summary.strip() and options.generate_recordings:
                text = self.db.compose_ai_text(
                    record.get("transcription", ""), record.get("recording_notes", "")
                )
                if text and text.strip():
                    summary = self._generate(
                        "recording_summary", record["id"],
                        prompts["recording"].replace("{text}", text).replace("{language}", prompts["language"]),
                        on_retry,
                    )
                    self.db.update_ai_content(record["id"], summary=summary)
                    recordings_count += 1
                    on_item_completed("recording", record.get("title", "Untitled"), summary)
                    on_recording_summary_completed(int(record["id"]), record.get("title", "Untitled"))
                    processed = True
            if summary:
                generated.append(f"Title: {record.get('title', 'Untitled')}\nSummary: {summary}")
        return recordings_count, generated, processed

    def _should_generate_daily(self, date, options, generated, processed) -> bool:
        existing = self.db.get_daily_summary(date, options.tags_filter)
        pending = not existing or (options.specific_dates and date in options.specific_dates)
        is_today = date == self.now().strftime("%Y-%m-%d")
        return bool(
            options.generate_daily
            and (pending or processed)
            and generated
            and not (options.exclude_today and is_today)
        )

    def _generate(self, operation, target, prompt, on_retry):
        return self.generate_content(
            provider=self.provider,
            settings=self.settings,
            prompt=prompt,
            operation_name=f"SummaryGenerator.{operation}[{target}]",
            on_retry=lambda delay, attempt, total, error: on_retry(
                operation, target, delay, attempt, total, error
            ),
        )

    def prepare_recordings_text(self, recordings: Iterable[dict]) -> str:
        return "".join(
            f"\n\n--- Recording: {record.get('title', 'Untitled')} ({record.get('created_at', '')}) ---\n"
            f"{self.db.compose_ai_text(record.get('transcription', ''), record.get('recording_notes', ''))}"
            for record in recordings
        )

    @staticmethod
    def week_dates(week_end: str) -> list[str]:
        end = datetime.strptime(week_end, "%Y-%m-%d")
        return [(end - timedelta(days=6 - index)).strftime("%Y-%m-%d") for index in range(7)]
