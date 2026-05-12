# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.

"""Default prompt templates shared by settings panels and widgets."""

DEFAULT_PROMPTS = {
    "summary": """Please provide a concise and structured summary of the following transcription.
Highlight key points, decisions made, and action items if any.
Maintain the original language of the transcription.

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
