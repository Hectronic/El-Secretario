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

from PyQt6.QtCore import QThread, pyqtSignal, QSettings
from src.ai_provider import get_ai_provider, generate_content_with_retry
import logging

class AIAssistant(QThread):
    task_completed = pyqtSignal(str, str) # type (summary/clean), result
    error = pyqtSignal(str)
    status_update = pyqtSignal(str)
    retry_wait = pyqtSignal(float, int, int, str)  # delay, attempt, total_attempts, error

    def __init__(self, api_key: str, task_type: str, text: str, model_name: str = "gemini-3-flash-preview"):
        """Initialize the AI Assistant.
        
        Note: api_key parameter is kept for backward compatibility but the actual
        provider configuration is read from QSettings.
        """
        super().__init__()
        self.task_type = task_type # "summary", "clean", or "weekly_summary"
        self.text = text
        # api_key and model_name are kept for backward compatibility
        # but the actual configuration comes from QSettings
        self._legacy_api_key = api_key
        self._legacy_model_name = model_name

    def run(self) -> None:
        try:
            settings = QSettings("Hectronic", "Secretario")
            provider = get_ai_provider(settings)

            # Default prompts (used if not customized in settings)
            default_prompts = {
                "summary": """Please provide a concise and structured summary of the following transcription.
Highlight key points, decisions made, and action items if any.
The summary MUST be written in {language}.

Transcription:
{text}""",
                "clean": """Please clean up the following transcription.
- Fix grammatical errors and punctuation.
- Remove filler words (uh, um, like).
- Improve readability while maintaining the original meaning and tone.
- Do NOT summarize, keep the full content.
- Maintain the original language of the transcription.

Transcription:
{text}""",
                "daily_summary": """As an expert assistant, provide a concise and structured daily summary based on the following recording summaries from today.
Group key information by topic, highlight important decisions, and list any pending action items.
The summary MUST be written in {language}.

Meeting Summaries:
{text}""",
                "weekly_summary": """As an expert assistant, provide a comprehensive and professional weekly summary based on the following recording content from this week.
Organize the summary by topic or day, highlighting key achievements, strategic decisions, and future action items.
The summary MUST be written in {language}.

Recordings Content:
{text}""",
                "task_extraction": """Extract only explicit, actionable next-step tasks from the content below.

Rules:
- Return a JSON array of strings and nothing else.
- Each task must be concrete, specific, and executable by one person.
- Start each task with a strong action verb.
- Include the object or expected deliverable when present.
- Keep each task concise, ideally under 16 words.
- Do not create generic reminders, summaries, topics, or inferred workstreams.
- Do not split one action into multiple tasks unless the content clearly separates them.
- Ignore background discussion, context, decisions, and vague intentions.
- If no clear actionable task exists, return [].
- Language: {language}

Content:
<transcription>
{text}
</transcription>

JSON:"""
            }

            # Load prompt from settings or use default
            prompt_template = settings.value(
                f"prompt_{self.task_type}", 
                default_prompts.get(self.task_type, "")
            )
            
            if not prompt_template:
                raise ValueError(f"Invalid task type: {self.task_type}")
            
            # Get system language
            language = settings.value("system_language", "Spanish")
            
            # Replace placeholders
            prompt = prompt_template.replace("{text}", str(self.text or ""))
            if "{language}" in prompt:
                prompt = prompt.replace("{language}", str(language or "Spanish"))

            logging.info(f"--- AI ASSISTANT TASK: {self.task_type} ---")
            logging.info(f"PROMPT SENT:\n{prompt}")

            def _on_retry(delay, attempt, total_attempts, error_text):
                self.status_update.emit(
                    f"{self.task_type}: waiting {delay:.1f}s before retry ({attempt + 1}/{total_attempts})"
                )
                self.retry_wait.emit(float(delay), int(attempt), int(total_attempts), str(error_text))

            result = generate_content_with_retry(
                provider=provider,
                settings=settings,
                prompt=prompt,
                operation_name=f"AIAssistant[{self.task_type}]",
                on_retry=_on_retry,
            )
            
            logging.info(f"RAW RESPONSE RECEIVED:\n{result}")
            
            self.task_completed.emit(str(self.task_type), str(result or ""))

        except Exception as e:
            logging.error(f"AIAssistant error: {e}", exc_info=True)
            self.error.emit(str(e))
