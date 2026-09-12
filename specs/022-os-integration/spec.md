# SPEC-022: OS Integration & Applications Menu

Status: Draft
Owner: TBD
Last updated: 2026-09-12

## Problem

After installation via source, the application lacks native OS integration. It needs to appear in the applications menu (Start Menu, Launchpad, GNOME App Drawer) with its proper icon, so users can launch it like any other application instead of running it from a terminal.

## Scope

- In scope: 
  - Generation of application shortcuts during the installation process (linked to SPEC-021).
  - High-quality icon assets (ICO for Windows, ICNS for macOS, PNG/SVG for Linux).
  - `.desktop` file creation for Ubuntu.
  - `.app` stub or Automator app creation for macOS.
  - Start Menu shortcut creation for Windows.
- Out of scope: Custom themes for the Qt application itself (covered in UI specs).

## User Stories

- As a user, I want to find the application in my Start Menu / App Drawer so I can launch it easily.
- As a user, I want the application to display a crisp, recognizable icon in the taskbar/dock when running.

## Acceptance Criteria

- Given the application is installed, when the user opens their OS applications menu, then "El Secretario" appears with the correct icon.
- Given the user clicks the shortcut, then the application launches successfully in the background without leaving a persistent terminal window open (unless intended for debugging).
- Given the application is running, then the taskbar/dock shows the correct icon instead of a generic Python or terminal icon.

## Architecture Notes

- Windows: The installer script uses COM objects in PowerShell or a small VBScript to create a `.lnk` file pointing to `pythonw.exe` running the main module.
- Linux: Create `~/.local/share/applications/el-secretario.desktop` pointing to the bash launcher, with `Icon=` pointing to the installed asset.
- macOS: Create a simple AppleScript or Automator wrapper exported as an Application that runs the shell script in the background.

## Test Plan

- Manual: Check Start Menu on Windows, App Drawer on Ubuntu, and Launchpad on macOS after installation. Verify that launching via the shortcut works and displays the correct icon in the dock/taskbar.

## Documentation

- Document how to rebuild shortcuts if they are accidentally deleted.
