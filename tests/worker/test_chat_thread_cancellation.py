import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import patch

from src.worker_components.threads import ChatThread


def test_chat_thread_cancels_an_in_flight_async_provider_request(qtbot):
    started = threading.Event()
    cancelled = threading.Event()

    class Provider:
        async def chat_async(self, _history, _query, _context):
            started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled.set()
                raise

    results = []
    errors = []
    with patch("src.ai_provider.get_ai_provider", return_value=Provider()), patch(
        "PyQt6.QtCore.QSettings"
    ):
        thread = ChatThread("", "question", "context", [])
        thread.finished.connect(results.append)
        thread.error.connect(errors.append)
        thread.start()
        assert started.wait(2)
        thread.cancel()
        assert thread.wait(3000)
        qtbot.waitUntil(lambda: results == [""], timeout=1000)

    assert cancelled.is_set()
    assert results == [""]
    assert errors == []
