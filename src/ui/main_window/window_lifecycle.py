"""Safe shutdown and Qt-event reactions for the main window."""

import logging

from PyQt6.QtCore import QEvent


class MainWindowLifecycleCoordinator:
    """Own non-visual window lifecycle work while Qt hooks stay on MainWindow."""

    def __init__(self, window):
        self.window = window

    def handle_change_event(self, event):
        if event.type() in (
            QEvent.Type.PaletteChange,
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.StyleChange,
        ) and hasattr(self.window, "floating_chat_bar"):
            self.window.chat_floating.refresh_floating_chat_bar()

    def handle_resize(self):
        self.window.chat_floating.reposition_floating_chat_bar()

    def cleanup_before_close(self):
        window = self.window
        logging.warning(
            "MainWindow.closeEvent triggered. tabs=%d queue_running=%s recorder_recording=%s",
            window.central_tabs.count(),
            window.summary_task_queue.is_running if window.summary_task_queue else None,
            window.recorder.is_recording if window.recorder else None,
        )
        window._sidebar_refresh_timer.stop()
        window._pending_history_reload = False
        window._pending_tag_reload = False

        self._stop_search_thread()
        self._cancel_summary_queue()
        self._cleanup_tabs_and_floating_chats()
        self._stop_recorder()
        self._release_optional_gpu_cache()
        logging.warning("MainWindow.closeEvent cleanup completed.")

    def _stop_search_thread(self):
        search_thread = self.window.search_thread
        if search_thread and search_thread.isRunning():
            try:
                search_thread.requestInterruption()
                search_thread.quit()
                search_thread.wait(3000)
            except Exception:
                logging.exception("Failed stopping search thread during closeEvent.")
        self.window.search_thread = None

    def _cancel_summary_queue(self):
        if self.window.summary_task_queue:
            self.window.summary_task_queue.cancel_all()
            logging.info("Summary task queue cancelled during closeEvent.")
        self.window.regen_worker = None

    def _cleanup_tabs_and_floating_chats(self):
        for index in range(self.window.central_tabs.count() - 1, -1, -1):
            self._cleanup_widget(self.window.central_tabs.widget(index))

        for host in list(self.window.floating_chat_hosts):
            self._cleanup_widget(host.property("chat_widget"))
            self.window.chat_floating.remove_floating_host(host)

    @staticmethod
    def _cleanup_widget(widget):
        if widget and hasattr(widget, "cleanup"):
            try:
                widget.cleanup()
            except Exception:
                logging.exception("Failed cleaning widget during closeEvent.")

    def _stop_recorder(self):
        recorder = self.window.recorder
        if recorder and recorder.is_recording:
            try:
                recorder.stop()
                logging.info("Active recorder stopped during closeEvent.")
            except Exception:
                logging.exception("Failed stopping recorder during closeEvent.")

    @staticmethod
    def _release_optional_gpu_cache():
        try:
            import gc
            import torch

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
