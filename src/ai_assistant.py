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

from PyQt6.QtCore import QThread, pyqtSignal, QSettings
from src.ai_provider import get_ai_provider

class AIAssistant(QThread):
    finished = pyqtSignal(str, str) # type (summary/clean), result
    error = pyqtSignal(str)

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

            if self.task_type == "summary":
                prompt = f"""
                Please provide a concise and structured summary of the following transcription.
                Highlight key points, decisions made, and action items if any.
                
                Transcription:
                {self.text}
                """
            elif self.task_type == "clean":
                prompt = f"""
                Please clean up the following transcription.
                - Fix grammatical errors and punctuation.
                - Remove filler words (uh, um, like).
                - Improve readability while maintaining the original meaning and tone.
                - Do NOT summarize, keep the full content.
                
                Transcription:
                {self.text}
                """
            elif self.task_type == "weekly_summary":
                prompt = f"""
                Please provide a comprehensive summary of the following recordings from this week.
                Group the summary by topic or day if relevant.
                Highlight key achievements, decisions, and action items.
                
                Recordings Content:
                {self.text}
                """
            else:
                raise ValueError("Invalid task type.")

            result = provider.generate_content(prompt)
            
            self.finished.emit(self.task_type, result)

        except Exception as e:
            self.error.emit(str(e))
