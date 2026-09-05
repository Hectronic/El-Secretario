"""Non-Qt state transitions for queue retry waits."""

from dataclasses import dataclass


@dataclass
class QueueRetryWaitState:
    """Track a retry countdown while leaving timer scheduling to the Qt adapter."""

    remaining_seconds: int = 0
    description: str = ""

    @property
    def is_waiting(self) -> bool:
        return self.remaining_seconds > 0

    def begin(self, seconds: int, description: str) -> None:
        self.remaining_seconds = max(0, int(seconds))
        self.description = str(description or "")

    def tick(self) -> bool:
        """Advance one second and return whether the wait remains active."""
        if not self.is_waiting:
            self.clear()
            return False
        self.remaining_seconds -= 1
        if not self.is_waiting:
            self.clear()
            return False
        return True

    def clear(self) -> None:
        self.remaining_seconds = 0
        self.description = ""

    def snapshot(self) -> tuple[bool, int, str]:
        return self.is_waiting, self.remaining_seconds, self.description
