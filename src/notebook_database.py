# Copyright (C) 2026 Héctor Álvarez López <hector.alvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Backwards-compatible facade for notebook persistence."""

from __future__ import annotations

from typing import Callable

from .persistence.notebooks import NotebookRepository


class NotebookDBManager:
    """Compatibility facade delegating notebook storage to ``NotebookRepository``."""

    def __init__(self, db_name: str = "notebooks.db"):
        self.notebooks = NotebookRepository(db_name)
        self.db_name = self.notebooks.db_name

    def get_connection(self):
        return self.notebooks.get_connection()

    def init_db(self):
        return self.notebooks.init_db()


def _delegated_method(method_name: str) -> Callable:
    def delegate(self, *args, **kwargs):
        return getattr(self.notebooks, method_name)(*args, **kwargs)

    delegate.__name__ = method_name
    delegate.__qualname__ = f"NotebookDBManager.{method_name}"
    delegate.__doc__ = getattr(NotebookRepository, method_name).__doc__
    return delegate


for _method_name, _method in NotebookRepository.__dict__.items():
    if callable(_method) and not _method_name.startswith("_") and _method_name not in {"get_connection", "init_db"}:
        setattr(NotebookDBManager, _method_name, _delegated_method(_method_name))
