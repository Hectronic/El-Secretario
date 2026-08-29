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

import unittest

from src.ui.chat.theme_styles import build_chat_widget_theme


class TestChatThemeStyles(unittest.TestCase):
    def test_dark_theme_palette(self):
        theme = build_chat_widget_theme(True)

        self.assertEqual(theme["header_bg"], "rgba(33, 150, 243, 0.15)")
        self.assertEqual(theme["title_color"], "#e8eef7")
        self.assertEqual(theme["display_bg"], "#1f232a")
        self.assertEqual(theme["display_text"], "#f3f6fb")

    def test_light_theme_palette(self):
        theme = build_chat_widget_theme(False)

        self.assertEqual(theme["header_bg"], "rgba(33, 150, 243, 0.10)")
        self.assertEqual(theme["title_color"], "#2b3b52")
        self.assertEqual(theme["display_bg"], "#ffffff")
        self.assertEqual(theme["display_text"], "#1a1c1e")


if __name__ == "__main__":
    unittest.main()
