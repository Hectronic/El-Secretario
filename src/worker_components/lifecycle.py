"""Shared terminal-outcome vocabulary for owned runtime operations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from uuid import uuid4


class TerminalStatus(StrEnum):
    SUCCEEDED = "succeeded"
    CANCELLED = "cancelled"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


@dataclass(frozen=True)
class TerminalOutcome:
    status: TerminalStatus
    operation_id: str
    user_message: str = ""
    retryable: bool = False
    preserved_work: bool = True

    def payload(self):
        return {"status": self.status.value, **asdict(self) | {"status": self.status.value}}


class TerminalOutcomeEmitter:
    """Make terminal emission idempotent when cancellation races cleanup."""

    def __init__(self, operation_id=None):
        self.operation_id = operation_id or uuid4().hex
        self.outcome = None

    def complete(self, status, *, user_message="", retryable=False, preserved_work=True):
        if self.outcome is not None:
            return None
        self.outcome = TerminalOutcome(
            status=TerminalStatus(status),
            operation_id=self.operation_id,
            user_message=str(user_message or ""),
            retryable=bool(retryable),
            preserved_work=bool(preserved_work),
        )
        return self.outcome
