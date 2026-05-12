from unittest.mock import MagicMock

from src.ui.main_window.summary_actions import SummaryActionsCoordinator


class _Window:
    def __init__(self):
        self.summary_task_queue = MagicMock()


def test_regenerate_summary_enqueues_daily_payload():
    window = _Window()
    coordinator = SummaryActionsCoordinator(window)
    data = {"date": "2026-05-11", "tags_filter": "ops"}

    coordinator.regenerate_summary(data)
    window.summary_task_queue.enqueue_daily_summary.assert_called_once_with(
        {"date": "2026-05-11", "tags_filter": "ops", "source": "welcome"}
    )


def test_regenerate_summary_ignores_payload_without_date():
    window = _Window()
    coordinator = SummaryActionsCoordinator(window)
    coordinator.regenerate_summary({"type": "daily"})
    window.summary_task_queue.enqueue_daily_summary.assert_not_called()
