# SPEC-021: Cross-Platform Installation Scripts

Status: Draft
Owner: TBD
Last updated: 2026-09-12

## Problem

Users currently need technical knowledge to set up the application (cloning the repo, creating a virtual environment, installing dependencies). We need a simple, one-click or single-command installation process that automates deploying the app from source on Windows, macOS, and Ubuntu.

## Scope

- In scope: 
  - Automated installation scripts (`install.bat`/`install.ps1` for Windows, `install.sh` for macOS/Ubuntu).
  - Cloning the repository from the `main` branch to a standard user directory (e.g., `%LOCALAPPDATA%\El-Secretario` or `~/.local/share/El-Secretario`).
  - Automatic creation of the Python virtual environment and installation of dependencies.
- Out of scope: Compiling the app into a standalone binary (e.g., via PyInstaller), since we are using a source-based distribution model.

## User Stories

- As a user, I want to run a single script that downloads and installs the application so I don't have to deal with the terminal or Python environments.
- As a user, I want the installation to automatically put the application in a standard path so it doesn't clutter my downloads or desktop folder.

## Acceptance Criteria

- Given a fresh OS environment, when the user runs the installation script, then the repository is cloned to the correct target directory.
- Given the repo is cloned, when the script continues, then a Python virtual environment is created and all requirements are successfully installed.
- Given the installation finishes, then the application is ready to be launched without further manual configuration.

## Architecture Notes

- Scripts should be idempotent: running the installer twice should safely update or verify the existing installation rather than failing.
- Windows: Use PowerShell or a Batch file.
- Linux/macOS: Use bash scripts.
- Rely on standard OS utilities (Git, Python 3) which the user must have installed, or the script should prompt them to install if missing.

## Test Plan

- Manual: Run the installation scripts on clean virtual machines for Windows 11, Ubuntu, and macOS to verify successful deployment.

## Documentation

- Update `README.md` to feature the new simple installation commands.
