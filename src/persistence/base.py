# Copyright (C) 2026 Héctor Álvarez López <hector.alvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Shared SQLite connection and repository composition primitives."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from os import PathLike
from typing import Protocol


class ConnectionProvider(Protocol):
    def get_connection(self): ...


class RepositoryBase:
    """Give a domain repository access to an existing SQLite connection provider."""

    def __init__(self, persistence: ConnectionProvider | str | PathLike[str]):
        if hasattr(persistence, "get_connection"):
            self._persistence = persistence
        else:
            self._persistence = PersistenceBase(str(persistence))

    @property
    def db_name(self):
        return self._persistence.db_name

    def get_connection(self):
        return self._persistence.get_connection()


class PersistenceBase:
    """Own a database path and initialize its shared application schema once."""

    def __init__(self, db_name: str = "transcriptions.db"):
        self.db_name = os.path.abspath(db_name)
        from .schema import SchemaManager

        SchemaManager(self).init_db()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_name, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
