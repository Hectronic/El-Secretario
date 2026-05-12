# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 3 or later.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <https://www.gnu.org/licenses/>.

from src.ui.filter_dialog import FilterDialog


def test_filter_dialog_collects_date_and_tags(qtbot):
    dialog = FilterDialog(["ops", "review"], current_date="2026-03-10", current_tags=["ops"])
    qtbot.addWidget(dialog)

    assert dialog.date_check.isChecked()
    filters = dialog.get_filters()

    assert filters["date"] == "2026-03-10"
    assert filters["tags"] == ["ops"]


def test_filter_dialog_without_date_returns_selected_tags(qtbot):
    dialog = FilterDialog(["ops", "review"], current_tags=["review"])
    qtbot.addWidget(dialog)

    filters = dialog.get_filters()

    assert filters["date"] is None
    assert filters["tags"] == ["review"]
