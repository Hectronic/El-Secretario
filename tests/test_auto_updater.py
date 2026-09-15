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

"""Tests for the automated update system."""

import os
import sys
import subprocess
import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QSettings

from src.auto_updater import (
    is_auto_update_enabled,
    check_for_updates,
    perform_update,
)
from src.ui.main_window.update_checker import UpdateCheckerThread


@pytest.fixture
def clean_env():
    """Ensure a clean environment for testing env vars."""
    old_val = os.environ.get("DISABLE_AUTO_UPDATE")
    if old_val is not None:
        del os.environ["DISABLE_AUTO_UPDATE"]
    yield
    if old_val is not None:
        os.environ["DISABLE_AUTO_UPDATE"] = old_val


def test_is_auto_update_enabled_default(clean_env):
    """Test that auto-update is enabled by default."""
    # Ensure any QSettings key is removed for clean test
    settings = QSettings("Hectronic", "Secretario")
    settings.remove("enable_auto_update")
    assert is_auto_update_enabled() is True


def test_is_auto_update_enabled_env_var(clean_env):
    """Test that DISABLE_AUTO_UPDATE env var disables auto-updates."""
    os.environ["DISABLE_AUTO_UPDATE"] = "1"
    assert is_auto_update_enabled() is False

    os.environ["DISABLE_AUTO_UPDATE"] = "true"
    assert is_auto_update_enabled() is False


def test_is_auto_update_enabled_qsettings(clean_env):
    """Test that QSettings overrides default but not env var."""
    settings = QSettings("Hectronic", "Secretario")
    
    settings.setValue("enable_auto_update", False)
    assert is_auto_update_enabled() is False

    settings.setValue("enable_auto_update", True)
    assert is_auto_update_enabled() is True

    # Env var should override even if settings say True
    os.environ["DISABLE_AUTO_UPDATE"] = "1"
    assert is_auto_update_enabled() is False


@patch("subprocess.run")
def test_check_for_updates_not_git(mock_run):
    """Test when we are not inside a git repository."""
    # Mock git rev-parse --is-inside-work-tree failing
    mock_run.return_value = MagicMock(returncode=1, stdout="")
    
    is_behind, reqs_changed, msg = check_for_updates()
    assert is_behind is False
    assert "Not inside a git repository" in msg


@patch("subprocess.run")
def test_check_for_updates_not_main_branch(mock_run):
    """Test when the current branch is not main."""
    # Mock is-inside-work-tree success, branch as "feature-branch"
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout="true"),
        MagicMock(returncode=0, stdout="feature-branch\n"),
    ]
    
    is_behind, reqs_changed, msg = check_for_updates()
    assert is_behind is False
    assert "Not on 'main' branch" in msg


@patch("subprocess.run")
def test_check_for_updates_fetch_failed(mock_run):
    """Test fetch failure (e.g. offline)."""
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout="true"),  # inside git
        MagicMock(returncode=0, stdout="main\n"),  # branch
        MagicMock(returncode=1),  # fetch failed
    ]
    
    is_behind, reqs_changed, msg = check_for_updates()
    assert is_behind is False
    assert "Failed to fetch" in msg


@patch("subprocess.run")
def test_check_for_updates_up_to_date(mock_run):
    """Test when local is up to date (no commits behind)."""
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout="true"),  # inside git
        MagicMock(returncode=0, stdout="main\n"),  # branch
        MagicMock(returncode=0),  # fetch success
        MagicMock(returncode=1),  # ancestor failed (local is not ancestor/already same/diverged)
    ]
    
    is_behind, reqs_changed, msg = check_for_updates()
    assert is_behind is False
    assert "Local repository is up to date" in msg


@patch("subprocess.run")
def test_check_for_updates_available_no_requirements_change(mock_run):
    """Test when update is available and requirements.txt did not change."""
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout="true"),  # inside git
        MagicMock(returncode=0, stdout="main\n"),  # branch
        MagicMock(returncode=0),  # fetch success
        MagicMock(returncode=0),  # is-ancestor success (behind)
        MagicMock(returncode=0, stdout="local_sha\n"),  # head rev
        MagicMock(returncode=0, stdout="remote_sha\n"),  # origin/main rev
        MagicMock(returncode=0, stdout="src/main.py\nsrc/ui.py\n"),  # diff file list
    ]
    
    is_behind, reqs_changed, msg = check_for_updates()
    assert is_behind is True
    assert reqs_changed is False
    assert msg == "Update available"


@patch("subprocess.run")
def test_check_for_updates_available_with_requirements_change(mock_run):
    """Test when update is available and requirements.txt has changed."""
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout="true"),  # inside git
        MagicMock(returncode=0, stdout="main\n"),  # branch
        MagicMock(returncode=0),  # fetch success
        MagicMock(returncode=0),  # is-ancestor success (behind)
        MagicMock(returncode=0, stdout="local_sha\n"),  # head rev
        MagicMock(returncode=0, stdout="remote_sha\n"),  # origin/main rev
        MagicMock(returncode=0, stdout="src/main.py\nrequirements.txt\n"),  # diff file list
    ]
    
    is_behind, reqs_changed, msg = check_for_updates()
    assert is_behind is True
    assert reqs_changed is True
    assert msg == "Update available"


@patch("subprocess.run")
def test_perform_update_success_no_pip(mock_run):
    """Test performing update successfully when requirements didn't change."""
    mock_run.return_value = MagicMock(returncode=0)
    
    success = perform_update(requirements_changed=False)
    assert success is True
    # Verify we pulled
    mock_run.assert_called_once()
    assert mock_run.call_args[0][0] == ["git", "pull", "origin", "main"]


@patch("subprocess.run")
def test_perform_update_success_with_pip(mock_run):
    """Test performing update successfully when requirements did change."""
    mock_run.side_effect = [
        MagicMock(returncode=0),  # pull success
        MagicMock(returncode=0),  # pip success
    ]
    
    success = perform_update(requirements_changed=True)
    assert success is True
    assert mock_run.call_count == 2


@patch("subprocess.run")
def test_perform_update_pull_failed(mock_run):
    """Test performing update when pulling fails."""
    mock_run.return_value = MagicMock(returncode=1)
    
    success = perform_update(requirements_changed=False)
    assert success is False


def test_update_checker_thread(qtbot):
    """Test the UpdateCheckerThread class logic and signals."""
    thread = UpdateCheckerThread()
    
    # Mock check_for_updates function
    with patch("src.ui.main_window.update_checker.check_for_updates") as mock_check:
        mock_check.return_value = (True, True, "Update available")
        
        # Monitor signals using qtbot
        with qtbot.wait_signal(thread.update_checked) as blocker:
            thread.start()
            
        assert blocker.args == [True, True, "Update available"]
        thread.wait()
