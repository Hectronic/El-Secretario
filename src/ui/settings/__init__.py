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

"""Settings panel package."""

from src.ui.settings.audio_panel import AudioSettingsPanel
from src.ui.settings.general_panel import GeneralSettingsPanel
from src.ui.settings.prompts_panel import PromptsSettingsPanel
from src.ui.settings.rag_panel import RAGSettingsPanel

__all__ = ["AudioSettingsPanel", "GeneralSettingsPanel", "PromptsSettingsPanel", "RAGSettingsPanel"]
