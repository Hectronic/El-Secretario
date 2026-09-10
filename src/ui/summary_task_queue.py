# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Backward-compatible import for the Qt summary-task queue facade."""

from src.app.summary_queue.helpers import (
    parse_task_extraction_result as _parse_task_extraction_result,
)
from src.app.summary_queue.helpers import (
    read_audio_duration_seconds as _read_audio_duration_seconds,
)
from src.ui.summary_queue.manager import SummaryTaskQueueManager

__all__ = [
    "SummaryTaskQueueManager",
    "_parse_task_extraction_result",
    "_read_audio_duration_seconds",
]
