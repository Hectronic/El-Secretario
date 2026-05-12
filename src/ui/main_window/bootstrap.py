"""Bootstrap helpers for the main window startup sequence."""


def bootstrap_main_window(window):
    """Run the post-construction startup sequence for ``MainWindow``.

    The goal is to keep ``MainWindow.__init__`` focused on dependency
    construction while this helper owns the deterministic startup order.
    """

    window._log_user_settings_snapshot("startup")
    window.load_history()
    window.refresh_tag_filter()
    window.load_chat_sessions()
    window.refresh_tasks_sidebar()
    window.load_notebooks()
    window._setup_task_status_bar()
    window._connect_task_queue_signals()
    window._enqueue_missing_previous_week_summary_if_enabled()
    window._enqueue_missing_previous_daily_summary_if_enabled()
    window.show_welcome_screen()
