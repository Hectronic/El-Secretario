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
# Avoid DLL conflicts and potential crashes on Windows with multiple OpenMP libraries.
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["ANONYMIZED_TELEMETRY"] = "False"
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Automatically add bundled FFmpeg binaries to path if they exist
if getattr(sys, 'frozen', False):
    ffmpeg_bin = resource_path("bin")
    if os.path.exists(ffmpeg_bin):
        os.environ["PATH"] += os.pathsep + ffmpeg_bin

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from src.ui.main_window import MainWindow
from src.logging_config import setup_logging
import logging

if __name__ == "__main__":
    setup_logging()
    logging.info("Application starting...")
    app = QApplication(sys.argv)
    
    # Use the helper to find the icon
    app_icon = QIcon(resource_path("logo.png"))
    app.setWindowIcon(app_icon)
    
    window = MainWindow()
    window.show()
    exit_code = app.exec()
    logging.info("Application exiting with code: %d", exit_code)
    sys.exit(exit_code)
