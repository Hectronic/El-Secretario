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
# along with this program.  See <https://www.gnu.org/licenses/>.

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from dataclasses import dataclass

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSlider, QStyle


PRIMARY_ACTION_CLASS = "calendar-primary-btn"
SECONDARY_ACTION_CLASS = "calendar-nav-btn"
DANGER_ACTION_CLASS = "record-del-btn"


@dataclass
class PlaybackControls:
    layout: QHBoxLayout
    play_btn: QPushButton
    pause_btn: QPushButton
    stop_btn: QPushButton
    slider: QSlider
    time_label: QLabel
    volume_slider: QSlider


def create_action_button(
    text,
    slot=None,
    *,
    style_class=None,
    min_height=None,
    min_width=None,
    tooltip=None,
    enabled=True,
    parent=None,
):
    button = QPushButton(text, parent)
    if style_class:
        button.setProperty("class", style_class)
    button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    if min_height is not None:
        button.setMinimumHeight(min_height)
    if min_width is not None:
        button.setMinimumWidth(min_width)
    if tooltip:
        button.setToolTip(tooltip)
    if slot is not None:
        button.clicked.connect(slot)
    button.setEnabled(enabled)
    return button


def create_media_button(parent, standard_icon, slot, *, enabled=False):
    button = QPushButton(parent)
    button.setIcon(parent.style().standardIcon(standard_icon))
    button.clicked.connect(slot)
    button.setEnabled(enabled)
    return button


def create_primary_action(text, slot=None, **kwargs):
    return create_action_button(
        text,
        slot,
        style_class=PRIMARY_ACTION_CLASS,
        **kwargs,
    )


def create_secondary_action(text, slot=None, **kwargs):
    return create_action_button(
        text,
        slot,
        style_class=SECONDARY_ACTION_CLASS,
        **kwargs,
    )


def create_danger_action(text, slot=None, **kwargs):
    return create_action_button(
        text,
        slot,
        style_class=DANGER_ACTION_CLASS,
        **kwargs,
    )


def create_playback_controls(
    parent,
    *,
    on_play,
    on_pause,
    on_stop,
    on_slider_moved,
    on_volume_changed,
):
    layout = QHBoxLayout()
    play_btn = create_media_button(parent, QStyle.StandardPixmap.SP_MediaPlay, on_play)
    layout.addWidget(play_btn)

    pause_btn = create_media_button(parent, QStyle.StandardPixmap.SP_MediaPause, on_pause)
    layout.addWidget(pause_btn)

    stop_btn = create_media_button(parent, QStyle.StandardPixmap.SP_MediaStop, on_stop)
    layout.addWidget(stop_btn)

    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(0, 0)
    slider.sliderMoved.connect(on_slider_moved)
    layout.addWidget(slider)

    time_label = QLabel("00:00 / 00:00")
    layout.addWidget(time_label)

    layout.addWidget(QLabel("Vol:"))
    volume_slider = QSlider(Qt.Orientation.Horizontal)
    volume_slider.setRange(0, 100)
    volume_slider.setValue(70)
    volume_slider.setFixedWidth(80)
    volume_slider.valueChanged.connect(on_volume_changed)
    on_volume_changed(0.7)
    layout.addWidget(volume_slider)

    return PlaybackControls(
        layout=layout,
        play_btn=play_btn,
        pause_btn=pause_btn,
        stop_btn=stop_btn,
        slider=slider,
        time_label=time_label,
        volume_slider=volume_slider,
    )
