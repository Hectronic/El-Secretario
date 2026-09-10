# Implementation Plan: Audio Capture and Import

**Branch**: `001-audio-capture-import` | **Status**: Implemented

Capture/import ownership is split between `src/ui/welcome/`, `src/ui/recording_in_progress/`, and main-window recording tabs. Qt lifecycle and platform guards are covered by recording integration tests.
