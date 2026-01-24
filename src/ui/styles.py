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


LIST_WIDGET_STYLE = """
    QListWidget {
        border: none;
        background-color: #2b2b2b;
        color: #eeeeee;
    }
    QListWidget::item {
        padding: 5px;
        border-bottom: 1px solid #3a3a3a;
    }
    QListWidget::item:hover {
        background-color: #3a3a3a;
    }
    QListWidget::item:selected {
        background-color: #4a4a4a;
    }
"""

TEXT_EDIT_STYLE = """
    QTextEdit {
        border: 1px solid #ccc;
        border-radius: 3px;
        padding: 10px;
    }
"""

BUTTON_PRIMARY_STYLE = """
    QPushButton {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        padding: 5px 15px;
    }
"""

BUTTON_DANGER_STYLE = """
    QPushButton {
        color: #f44336;
    }
"""

NEW_CHAT_BUTTON_STYLE = """
    QPushButton {
        background-color: #4CAF50; 
        color: white; 
        font-weight: bold; 
        padding: 8px;
    }
"""
