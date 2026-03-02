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
import threading
import faulthandler
from pathlib import Path

LOG_DIR = Path("log")
LOG_FILE = LOG_DIR / "app.log"
CRASH_LOG_FILE = LOG_DIR / "crash.log"
_CRASH_FP = None

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

    # Log exceptions raised from Python threads that would otherwise be easy to miss.
    def thread_exception_hook(args):
        logging.error(
            "Unhandled thread exception in %s",
            getattr(args.thread, "name", "<unknown>"),
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    threading.excepthook = thread_exception_hook

    # Capture low-level crashes (segfault/access violation/abort) when possible.
    try:
        global _CRASH_FP
        _CRASH_FP = open(CRASH_LOG_FILE, "w", encoding="utf-8")
        faulthandler.enable(file=_CRASH_FP, all_threads=True)
        logging.info("Faulthandler enabled. Crash log file: %s", CRASH_LOG_FILE.absolute())
    except Exception:
        logging.exception("Could not enable faulthandler.")

    logging.info("Logging initialized. Log file: %s", LOG_FILE.absolute())
