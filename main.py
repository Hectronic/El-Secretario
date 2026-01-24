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
os.environ["ANONYMIZED_TELEMETRY"] = "False"
import sys
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.logging_config import setup_logging
import logging

if __name__ == "__main__":
    setup_logging()
    logging.info("Application starting...")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    exit_code = app.exec()
    logging.info("Application exiting with code: %d", exit_code)
    sys.exit(exit_code)
