"""Local recurring meeting scheduling and reminder lifecycle."""

from .recurrence import expand_occurrences, next_occurrences, validate_template

__all__ = ["MeetingScheduler", "expand_occurrences", "next_occurrences", "validate_template"]


def __getattr__(name):
    # Keep recurrence validation importable from persistence without importing
    # the scheduler back into the persistence package during initialization.
    if name == "MeetingScheduler":
        from .scheduler import MeetingScheduler

        return MeetingScheduler
    raise AttributeError(name)
