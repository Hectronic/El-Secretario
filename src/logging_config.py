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

import logging
import os
import shutil
import sys
from pathlib import Path

LOG_DIR = Path("log")
LOG_FILE = LOG_DIR / "app.log"

def setup_logging():
    """
    Sets up the logging configuration.
    Clears the log directory on startup.
    Configures logging to file and console.
    Sets up a global exception hook.
    """
    # Clear and recreate log directory
    if LOG_DIR.exists():
        shutil.rmtree(LOG_DIR)
    LOG_DIR.mkdir(exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Log unhandled exceptions
    def exception_hook(exctype, value, traceback):
        logging.error("Uncaught exception:", exc_info=(exctype, value, traceback))
        sys.__excepthook__(exctype, value, traceback)

    sys.excepthook = exception_hook

    logging.info("Logging initialized. Log file: %s", LOG_FILE.absolute())
