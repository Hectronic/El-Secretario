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

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QPushButton


def create_big_button(text, color, callback, width=200, height=150, class_name=None):
    btn = QPushButton(text)
    if class_name:
        btn.setProperty("class", class_name)
    btn.setFixedSize(width, height)

    if not class_name:
        btn.setStyleSheet(
            f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    font-size: 16px;
                    font-weight: bold;
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    background-color: {color}cc;
                }}
            """
        )
    btn.clicked.connect(callback)
    return btn


def create_round_button(text, color, callback, size=120, class_name=None):
    btn = QPushButton(text)
    if class_name:
        btn.setProperty("class", class_name)
    btn.setFixedSize(size, size)

    if not class_name:
        btn.setStyleSheet(
            f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    font-size: 20px;
                    font-weight: bold;
                    border-radius: {size // 2}px;
                    border: 5px solid #fff;
                }}
                QPushButton:hover {{
                    background-color: {color}cc;
                    border-color: #eee;
                }}
                QPushButton:pressed {{
                    background-color: {color}aa;
                    border-color: #ccc;
                }}
            """
        )
    btn.clicked.connect(callback)
    return btn


def create_squircle_button(text, color, callback, width=100, height=90, class_name=None):
    btn = QPushButton(text)
    if class_name:
        btn.setProperty("class", class_name)
    btn.setFixedSize(width, height)
    border_radius = int(height * 0.25)

    if not class_name:
        bg = QColor(color)
        hover_bg = bg.lighter(115).name()
        pressed_bg = bg.darker(110).name()

        btn.setStyleSheet(
            f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    font-size: 20px;
                    font-weight: bold;
                    border-top-right-radius: {border_radius}px;
                    border-bottom-right-radius: {border_radius}px;
                    border-top-left-radius: 0px;
                    border-bottom-left-radius: 0px;
                    border: 2px solid #555;
                    border-left: none;
                }}
                QPushButton:hover {{
                    background-color: {hover_bg};
                    border: 2px solid #777;
                    border-left: none;
                }}
                QPushButton:pressed {{
                    background-color: {pressed_bg};
                    border: 2px solid #999;
                    border-left: none;
                }}
            """
        )
    btn.clicked.connect(callback)
    return btn
