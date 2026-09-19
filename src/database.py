# Copyright (C) 2026 Héctor Álvarez López <hector.alvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Backwards-compatible facade for application SQLite persistence."""

from __future__ import annotations

from typing import Callable

from .persistence import (
    ChatSessionsRepository,
    PersistenceBase,
    QueueJobsRepository,
    RAGIndexRepository,
    RecordsRepository,
    SchemaManager,
    SummariesRepository,
    TasksRepository,
    TranscriptionLogsRepository,
)


class DBManager(PersistenceBase):
    """Compatibility facade that delegates persistence calls to aggregate repositories."""

    _repository_types = {
        "records": RecordsRepository,
        "chat_sessions": ChatSessionsRepository,
        "transcription_logs": TranscriptionLogsRepository,
        "summaries": SummariesRepository,
        "tasks": TasksRepository,
        "rag_index": RAGIndexRepository,
        "queue_jobs": QueueJobsRepository,
    }

    def __init__(self, db_name: str = "transcriptions.db"):
        super().__init__(db_name)
        for attribute, repository_type in self._repository_types.items():
            setattr(self, attribute, repository_type(self))

    def init_db(self):
        """Re-run schema initialization for callers of the historical facade API."""
        return SchemaManager(self).init_db()

    def _week_sunday(self, date_str):
        return self.tasks._week_sunday(date_str)

    @staticmethod
    def compose_ai_text(transcription, recording_notes):
        return RecordsRepository.compose_ai_text(transcription, recording_notes)


def _delegated_method(repository_attribute: str, method_name: str) -> Callable:
    def delegate(self, *args, **kwargs):
        return getattr(getattr(self, repository_attribute), method_name)(*args, **kwargs)

    delegate.__name__ = method_name
    delegate.__qualname__ = f"DBManager.{method_name}"
    delegate.__doc__ = getattr(DBManager._repository_types[repository_attribute], method_name).__doc__
    return delegate


for _repository_attribute, _repository_type in DBManager._repository_types.items():
    for _method_name, _method in _repository_type.__dict__.items():
        if callable(_method) and not _method_name.startswith("_") and _method_name != "compose_ai_text":
            setattr(DBManager, _method_name, _delegated_method(_repository_attribute, _method_name))
