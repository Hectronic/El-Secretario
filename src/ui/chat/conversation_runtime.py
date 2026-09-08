# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Lifecycle adapter for the asynchronous chat completion worker."""

from dataclasses import dataclass
from typing import Callable, Optional

from PyQt6.QtCore import QSettings

from src.ai_provider import validate_ai_provider_config
from src.worker_components.threads import ChatThread


@dataclass(frozen=True)
class ChatStartResult:
    """Result of asking the runtime to start a chat completion."""

    started: bool
    validation_error: Optional[str] = None


class ChatConversationRuntime:
    """Validate configuration and own one active ``ChatThread`` at a time.

    The widget keeps presentation and persistence responsibilities.  This adapter
    owns the provider precondition, worker signal wiring, and safe worker cleanup
    so those runtime concerns are independently testable.
    """

    def __init__(
        self,
        thread_factory=None,
        provider_validator: Optional[Callable] = None,
        settings_factory=None,
    ):
        self._thread_factory = thread_factory or ChatThread
        self._provider_validator = provider_validator or validate_ai_provider_config
        self._settings_factory = settings_factory or QSettings
        self.thread = None

    def start(self, query, context_text, history, on_finished, on_error, on_started=None):
        settings = self._settings_factory("Hectronic", "Secretario")
        is_valid, error_message = self._provider_validator(settings)
        if not is_valid:
            return ChatStartResult(started=False, validation_error=error_message)

        if self.thread and self.thread.isRunning():
            return ChatStartResult(started=False)

        self.thread = self._thread_factory("", query, context_text, history)
        self.thread.finished.connect(on_finished)
        self.thread.error.connect(on_error)
        self.thread.finished.connect(self._clear_thread)
        self.thread.error.connect(self._clear_thread)
        if on_started:
            on_started()
        self.thread.start()
        return ChatStartResult(started=True)

    def _clear_thread(self, *_args):
        thread = self.thread
        self.thread = None
        if thread:
            thread.deleteLater()

    def cleanup(self):
        thread = self.thread
        if not thread:
            return
        if thread.isRunning():
            try:
                thread.requestInterruption()
                thread.quit()
                thread.wait(3000)
            except Exception:
                pass
        try:
            thread.deleteLater()
        except Exception:
            pass
        self.thread = None
