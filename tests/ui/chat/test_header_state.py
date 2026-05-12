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

from src.ui.chat.header_state import build_chat_header_state


class TestChatHeaderState(unittest.TestCase):
    def test_tab_state(self):
        state = build_chat_header_state("tab", False)

        self.assertFalse(state["header_visible"])
        self.assertEqual(state["mode_btn_text"], "↗")
        self.assertEqual(state["minimize_btn_text"], "_")
        self.assertEqual(state["layout_margin"], 0)

    def test_floating_state(self):
        state = build_chat_header_state("floating", False)

        self.assertTrue(state["header_visible"])
        self.assertEqual(state["mode_btn_text"], "⇱")
        self.assertEqual(state["minimize_btn_text"], "_")
        self.assertTrue(state["minimize_visible"])
        self.assertEqual(state["layout_margin"], 1)

    def test_floating_minimized_state(self):
        state = build_chat_header_state("floating", True)

        self.assertTrue(state["header_visible"])
        self.assertEqual(state["minimize_btn_text"], "□")
        self.assertEqual(state["minimize_btn_tooltip"], "Restore chat")
        self.assertEqual(state["cursor"], "pointing")
        self.assertEqual(state["content_visible"], False)


if __name__ == "__main__":
    unittest.main()
