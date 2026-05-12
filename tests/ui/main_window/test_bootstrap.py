from src.ui.main_window.bootstrap import bootstrap_main_window


class _Window:
    def __init__(self):
        self.calls = []

    def _log_user_settings_snapshot(self, context):
        self.calls.append(("_log_user_settings_snapshot", context))

    def load_history(self):
        self.calls.append(("load_history",))

    def refresh_tag_filter(self):
        self.calls.append(("refresh_tag_filter",))

    def load_chat_sessions(self):
        self.calls.append(("load_chat_sessions",))

    def refresh_tasks_sidebar(self):
        self.calls.append(("refresh_tasks_sidebar",))

    def load_notebooks(self):
        self.calls.append(("load_notebooks",))

    def _setup_task_status_bar(self):
        self.calls.append(("_setup_task_status_bar",))

    def _connect_task_queue_signals(self):
        self.calls.append(("_connect_task_queue_signals",))

    def _enqueue_missing_previous_week_summary_if_enabled(self):
        self.calls.append(("_enqueue_missing_previous_week_summary_if_enabled",))

    def _enqueue_missing_previous_daily_summary_if_enabled(self):
        self.calls.append(("_enqueue_missing_previous_daily_summary_if_enabled",))

    def show_welcome_screen(self):
        self.calls.append(("show_welcome_screen",))


def test_bootstrap_main_window_runs_startup_sequence_in_order():
    window = _Window()

    bootstrap_main_window(window)

    assert window.calls == [
        ("_log_user_settings_snapshot", "startup"),
        ("load_history",),
        ("refresh_tag_filter",),
        ("load_chat_sessions",),
        ("refresh_tasks_sidebar",),
        ("load_notebooks",),
        ("_setup_task_status_bar",),
        ("_connect_task_queue_signals",),
        ("_enqueue_missing_previous_week_summary_if_enabled",),
        ("_enqueue_missing_previous_daily_summary_if_enabled",),
        ("show_welcome_screen",),
    ]
