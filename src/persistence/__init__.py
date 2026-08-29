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


"""Persistence repositories used by the backwards-compatible DBManager facade."""

from .base import PersistenceBase
from .chats import ChatSessionsRepository
from .logs import TranscriptionLogsRepository
from .records import RecordsRepository
from .schema import SchemaManager
from .summaries import SummariesRepository
from .tasks import TasksRepository

__all__ = [
    "PersistenceBase",
    "SchemaManager",
    "RecordsRepository",
    "ChatSessionsRepository",
    "TranscriptionLogsRepository",
    "SummariesRepository",
    "TasksRepository",
]
