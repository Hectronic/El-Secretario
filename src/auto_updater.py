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

"""Automated update system for El Secretario."""

import os
import sys
import subprocess
import logging

try:
    from PyQt6.QtCore import QSettings
    HAS_PYQT = True
except ImportError:
    HAS_PYQT = False

logger = logging.getLogger("ElSecretario.AutoUpdater")


def is_auto_update_enabled() -> bool:
    """Check if the auto-updater is enabled by settings or environment variables."""
    # Environment variable check overrides all settings
    env_disable = os.environ.get("DISABLE_AUTO_UPDATE")
    if env_disable in ("1", "true", "TRUE", "True"):
        return False

    if HAS_PYQT:
        try:
            settings = QSettings("Hectronic", "Secretario")
            val = settings.value("enable_auto_update", True)
            if isinstance(val, str):
                return val.lower() != "false"
            return bool(val)
        except Exception:
            pass
    return True


def check_for_updates(timeout_sec: int = 5) -> tuple[bool, bool, str]:
    """Check if local main is behind origin/main.

    Returns:
        tuple[is_behind, requirements_changed, message]
    """
    try:
        # Check if we are inside a git repository
        res = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        if res.returncode != 0 or "true" not in res.stdout:
            return False, False, "Not inside a git repository"

        # Check current branch
        branch_res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        current_branch = branch_res.stdout.strip()
        # If not on main, we don't automatically update to prevent mess-ups
        if current_branch != "main":
            return False, False, f"Not on 'main' branch (current: {current_branch})"

        # Fetch origin main
        # We redirect output to devnull to keep it transparent
        fetch_res = subprocess.run(
            ["git", "fetch", "origin", "main"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout_sec,
        )
        if fetch_res.returncode != 0:
            return False, False, "Failed to fetch from remote (possibly offline)"

        # Check if local is behind origin/main
        # If HEAD is behind, git merge-base --is-ancestor HEAD origin/main returns 0
        ancestor_res = subprocess.run(
            ["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"],
            timeout=timeout_sec,
        )
        if ancestor_res.returncode != 0:
            return False, False, "Local repository is up to date or diverged"

        # Verify HEAD and origin/main are not identical
        head_rev = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=timeout_sec
        ).stdout.strip()
        origin_rev = subprocess.run(
            ["git", "rev-parse", "origin/main"], capture_output=True, text=True, timeout=timeout_sec
        ).stdout.strip()

        if head_rev == origin_rev:
            return False, False, "Up to date"

        # Check if requirements.txt changed between HEAD and origin/main
        diff_res = subprocess.run(
            ["git", "diff", "--name-only", "HEAD", "origin/main"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        requirements_changed = "requirements.txt" in diff_res.stdout.splitlines()

        return True, requirements_changed, "Update available"

    except subprocess.TimeoutExpired:
        return False, False, "Connection timed out during update check"
    except Exception as e:
        return False, False, f"Error checking for updates: {e}"


def perform_update(requirements_changed: bool) -> bool:
    """Pull origin main and install dependencies if requirements.txt changed."""
    print("[INFO] Update found. Applying updates transparently...")
    try:
        # Run git pull
        pull_res = subprocess.run(
            ["git", "pull", "origin", "main"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
        if pull_res.returncode != 0:
            print("[WARNING] Failed to pull updates. Falling back to local version.")
            return False

        print("[INFO] Successfully updated code.")

        if requirements_changed:
            print("[INFO] Dependency changes detected. Updating venv (pip install -r requirements.txt)...")
            pip_res = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=120,
            )
            if pip_res.returncode != 0:
                print("[WARNING] Failed to update dependencies. Some features might not work.")
                return False
            print("[INFO] Dependencies updated successfully.")

        return True

    except Exception as e:
        print(f"[WARNING] Error performing update: {e}")
        return False


def main():
    """Main entry point for early-stage update checker."""
    if not is_auto_update_enabled():
        return

    is_behind, reqs_changed, msg = check_for_updates()
    if is_behind:
        perform_update(reqs_changed)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
