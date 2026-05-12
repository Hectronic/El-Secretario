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

from unittest.mock import MagicMock

from PyQt6.QtWidgets import QDialog

from src.ui.chat.add_context_dialog import AddContextDialog


def _make_dialog(qtbot, notebooks=None, tags=None):
    db = MagicMock()
    notebook_db = MagicMock()
    notebook_db.get_notebooks.return_value = notebooks or []
    db.get_all_tags.return_value = tags or []
    dialog = AddContextDialog(db, notebook_db)
    qtbot.addWidget(dialog)
    return dialog


def test_add_context_dialog_selects_notebook(qtbot):
    dialog = _make_dialog(qtbot, notebooks=[{"id": 1, "name": "Notebook 1"}])
    dialog.tabs.setCurrentIndex(0)
    dialog.nb_list.setCurrentRow(0)

    dialog.on_accept()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.selected_context == {"type": "notebook", "value": 1, "label": "Notebook 1"}


def test_add_context_dialog_selects_tag(qtbot):
    dialog = _make_dialog(qtbot, tags=["urgent"])
    dialog.tabs.setCurrentIndex(1)
    dialog.tag_list.setCurrentRow(0)

    dialog.on_accept()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.selected_context == {"type": "tag", "value": "urgent", "label": "urgent"}


def test_add_context_dialog_selects_date(qtbot):
    dialog = _make_dialog(qtbot)
    dialog.tabs.setCurrentIndex(2)
    dialog.date_edit.setDate(dialog.date_edit.date().addDays(-1))

    dialog.on_accept()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.selected_context["type"] == "date"
    assert dialog.selected_context["value"] == dialog.date_edit.date().toString("yyyy-MM-dd")


def test_add_context_dialog_rejects_without_selection(qtbot):
    dialog = _make_dialog(qtbot)
    dialog.tabs.setCurrentIndex(0)

    dialog.on_accept()

    assert dialog.result() == QDialog.DialogCode.Rejected
