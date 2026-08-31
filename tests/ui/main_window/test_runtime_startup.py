# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
from unittest.mock import MagicMock

from src.ui.main_window.runtime_startup import RuntimeStartupCoordinator


def test_disabled_rag_updates_runtime_flags_and_dependents(monkeypatch):
    window = MagicMock()
    window.central_tabs.count.return_value = 0
    coordinator = RuntimeStartupCoordinator(window)

    coordinator.build_rag_engine(
        {
            "enabled": False,
            "safe_delete_mode": False,
            "subprocess_upsert_mode": True,
            "subprocess_query_mode": False,
        },
        reason="reload",
    )

    assert os.environ["EL_SECRETARIO_CHROMA_SAFE_DELETE"] == "0"
    assert os.environ["EL_SECRETARIO_RAG_SUBPROCESS_UPSERT"] == "1"
    assert os.environ["EL_SECRETARIO_RAG_SUBPROCESS_QUERY"] == "0"
    assert window.rag is None
    window.summary_task_queue.set_rag_engine.assert_called_once_with(None)
    window.handle_status_message.assert_called_once_with("RAG disabled from settings.")


def test_startup_daily_summary_is_enqueued_only_when_enabled(monkeypatch):
    window = MagicMock()
    settings = MagicMock()
    settings.value.side_effect = lambda key, default=None, type=None: (
        True if key == "startup_enqueue_previous_daily_summary" else default
    )
    window.db.get_latest_recording_day_without_daily_summary.return_value = "2026-08-28"
    monkeypatch.setattr("src.ui.main_window.runtime_startup.QSettings", lambda *_: settings)

    RuntimeStartupCoordinator(window).enqueue_missing_previous_daily_summary_if_enabled()

    window.summary_task_queue.enqueue_daily_summary.assert_called_once_with(
        {"date": "2026-08-28", "tags_filter": "", "source": "startup"}
    )
