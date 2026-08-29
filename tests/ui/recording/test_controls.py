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

from PyQt6.QtWidgets import QApplication, QStyle, QWidget

from src.ui.recording.controls import (
    create_danger_action,
    create_media_button,
    create_playback_controls,
    create_primary_action,
    create_secondary_action,
)


APP = QApplication.instance() or QApplication([])


def test_create_action_button_applies_shared_visual_contract():
    parent = QWidget()
    calls = []
    try:
        button = create_primary_action(
            "Save",
            lambda: calls.append("clicked"),
            min_height=36,
            min_width=110,
            tooltip="Persist changes",
            enabled=False,
            parent=parent,
        )

        assert button.text() == "Save"
        assert button.property("class") == "calendar-primary-btn"
        assert button.minimumHeight() == 36
        assert button.minimumWidth() == 110
        assert button.toolTip() == "Persist changes"
        assert not button.isEnabled()

        button.setEnabled(True)
        button.click()
        assert calls == ["clicked"]
    finally:
        parent.close()




def test_semantic_action_helpers_apply_expected_style_classes():
    parent = QWidget()
    try:
        primary = create_primary_action("Primary", parent=parent)
        secondary = create_secondary_action("Secondary", parent=parent)
        danger = create_danger_action("Danger", parent=parent)

        assert primary.property("class") == "calendar-primary-btn"
        assert secondary.property("class") == "calendar-nav-btn"
        assert danger.property("class") == "record-del-btn"
    finally:
        parent.close()



def test_create_playback_controls_returns_shared_recording_controls():
    parent = QWidget()
    calls = []
    volume_values = []
    try:
        controls = create_playback_controls(
            parent,
            on_play=lambda: calls.append("play"),
            on_pause=lambda: calls.append("pause"),
            on_stop=lambda: calls.append("stop"),
            on_slider_moved=lambda value: calls.append(("seek", value)),
            on_volume_changed=volume_values.append,
        )

        assert controls.layout.count() == 7
        assert controls.time_label.text() == "00:00 / 00:00"
        assert controls.slider.minimum() == 0
        assert controls.slider.maximum() == 0
        assert controls.volume_slider.value() == 70
        assert controls.volume_slider.width() <= controls.volume_slider.maximumWidth() or controls.volume_slider.maximumWidth() >= 80
        assert volume_values == [0.7]

        controls.play_btn.setEnabled(True)
        controls.pause_btn.setEnabled(True)
        controls.stop_btn.setEnabled(True)
        controls.play_btn.click()
        controls.pause_btn.click()
        controls.stop_btn.click()
        controls.slider.sliderMoved.emit(42)

        assert calls == ["play", "pause", "stop", ("seek", 42)]
    finally:
        parent.close()

def test_create_media_button_uses_parent_standard_icon_and_disabled_default():
    parent = QWidget()
    calls = []
    try:
        button = create_media_button(
            parent,
            QStyle.StandardPixmap.SP_MediaPlay,
            lambda: calls.append("play"),
        )

        assert not button.icon().isNull()
        assert not button.isEnabled()
        button.setEnabled(True)
        button.click()
        assert calls == ["play"]
    finally:
        parent.close()
