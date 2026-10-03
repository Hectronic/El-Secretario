"""State snapshots and safe command dispatch for system-tray actions."""

from __future__ import annotations

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QInputDialog, QMessageBox

from src.persistence.meetings import parse_utc, utc_now
from src.ui.notebook_widget import NotebookWidget
from src.ui.recording_in_progress_widget import RecordingInProgressWidget
from src.ui.welcome_widget import WelcomeWidget


class TrayQuickActionsCoordinator:
    """Resolve live application state and route tray commands to feature owners.

    Snapshots contain values and tab indexes only. Each dispatch looks up the
    current widget again so an action can never retain a destroyed tab.
    """

    def __init__(self, window):
        self.window = window
        self._closed = False

    def snapshot(self):
        recording_index, recording_widget = self._active_recording()
        notebook_index, notebook_widget = self._active_audio_note()
        recorder_busy = bool(getattr(self.window.recorder, "is_recording", False))
        recording_active = recording_widget is not None or notebook_widget is not None or recorder_busy
        recording_paused = bool(
            recording_widget is not None
            and getattr(recording_widget.recorder, "is_paused", False)
        )
        elapsed = 0
        recording_title = ""
        if recording_widget is not None:
            elapsed = int(getattr(recording_widget, "duration_seconds", 0))
            title_input = getattr(recording_widget, "title_input", None)
            recording_title = (
                title_input.text().strip()
                if title_input is not None
                else str(getattr(recording_widget, "config", {}).get("title", "")).strip()
            )
        elif notebook_widget is not None:
            elapsed = int(getattr(notebook_widget, "recording_seconds", 0))

        productivity = getattr(self.window, "productivity", None)
        service = getattr(productivity, "service", None)
        pomodoro_available = service is not None
        pomodoro_active = bool(service and service.state in ("running", "paused"))
        pomodoro_remaining = int(service.remaining_seconds) if pomodoro_active else 0
        break_service = getattr(productivity, "break_service", None)
        meeting = self._next_meeting(productivity)

        notebook_available = getattr(self.window, "notebook_db", None) is not None
        if self._closed:
            recording_active = False
            pomodoro_available = False
            meeting = None

        return {
            "recording_active": recording_active,
            "recording_paused": recording_paused,
            "recording_elapsed": elapsed,
            "recording_title": recording_title,
            "recording_index": recording_index,
            "recording_kind": "capture" if recording_widget is not None else "audio_note" if notebook_widget is not None else "busy",
            "recording_controllable": recording_widget is not None or notebook_widget is not None,
            "audio_capture_available": not recorder_busy and not recording_active,
            "pomodoro_available": pomodoro_available,
            "pomodoro_active": pomodoro_active,
            "pomodoro_state": service.state if service is not None else "unavailable",
            "pomodoro_title": service.title if service is not None and pomodoro_active else "",
            "pomodoro_remaining": pomodoro_remaining,
            "pomodoro_recovery": bool(service and service.recovery_required),
            "pomodoro_can_start": bool(
                service
                and service.state not in ("running", "paused")
                and not service.recovery_required
                and not (break_service and break_service.state in ("running", "paused"))
            ),
            "meeting": meeting,
            "notebook_available": notebook_available,
        }

    def _active_recording(self):
        tabs = getattr(self.window, "central_tabs", None)
        if tabs is None:
            return -1, None
        for index in range(tabs.count()):
            widget = tabs.widget(index)
            if isinstance(widget, RecordingInProgressWidget) and widget.recording_started:
                return index, widget
        return -1, None

    def _active_audio_note(self):
        tabs = getattr(self.window, "central_tabs", None)
        if tabs is None:
            return -1, None
        for index in range(tabs.count()):
            widget = tabs.widget(index)
            if isinstance(widget, NotebookWidget) and getattr(widget.recorder, "is_recording", False):
                return index, widget
        return -1, None

    @staticmethod
    def _next_meeting(productivity):
        scheduler = getattr(productivity, "meeting_scheduler", None)
        repository = getattr(scheduler, "repository", None)
        if repository is None:
            return None
        try:
            now = utc_now()
            occurrences = repository.list_occurrences(
                states=("scheduled", "notified", "snoozed", "missed")
            )
            candidates = []
            for occurrence in occurrences:
                scheduled = parse_utc(occurrence["scheduled_at_utc"])
                if occurrence["state"] == "missed":
                    due = True
                elif scheduled < now and occurrence["state"] == "scheduled":
                    due = parse_utc(occurrence["reminder_at_utc"]) <= now
                elif occurrence["state"] == "notified":
                    due = True
                elif occurrence["state"] == "snoozed":
                    snoozed_until = occurrence.get("snoozed_until_utc")
                    due = bool(snoozed_until and parse_utc(snoozed_until) <= now)
                else:
                    due = parse_utc(occurrence["reminder_at_utc"]) <= now
                if scheduled >= now or due:
                    occurrence["due"] = due
                    occurrence["snoozable"] = occurrence["state"] in ("notified", "snoozed")
                    candidates.append((scheduled, occurrence))
            due_items = [item for item in candidates if item[1]["due"]]
            if due_items:
                return min(due_items, key=lambda item: item[0])[1]
            return min(candidates, key=lambda item: item[0])[1] if candidates else None
        except (KeyError, TypeError, ValueError, RuntimeError):
            return None

    def dispatch(self, command, payload=None):
        """Run one command against current state, rejecting stale menu actions."""
        if self._closed:
            return False
        actions = {
            "start_recording": self.start_recording,
            "pause_recording": self.toggle_recording_pause,
            "stop_recording": self.stop_recording,
            "cancel_recording": self.cancel_recording,
            "open_recording": self.open_recording,
            "new_text_note": self.new_text_note,
            "new_audio_note": self.new_audio_note,
            "start_pomodoro": self.start_pomodoro,
            "toggle_pomodoro": self.toggle_pomodoro,
            "finish_pomodoro": self.finish_pomodoro,
            "cancel_pomodoro": self.cancel_pomodoro,
            "start_meeting": lambda: self.start_meeting(payload),
            "snooze_meeting": lambda: self.snooze_meeting(payload),
            "dismiss_meeting": lambda: self.dismiss_meeting(payload),
            "open_meeting": lambda: self.open_meeting(payload),
            "open_app": self.open_app,
            "timeline": lambda: self._navigate("open_timeline_tab"),
            "tasks": lambda: self._navigate("open_tasks_tab"),
            "settings": lambda: self._navigate("open_settings_tab"),
        }
        callback = actions.get(command)
        return callback() if callback else False

    def _status(self, message, *, error=False):
        window = self.window
        handler = getattr(window, "handle_status_message", None)
        if callable(handler):
            handler(message)
        manager = getattr(window, "system_tray_manager", None)
        if manager:
            manager.show_message("El Secretario", message)
        if error:
            self.open_app()

    def open_app(self):
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def _navigate(self, method_name):
        self.open_app()
        callback = getattr(self.window, method_name, None)
        return callback() if callable(callback) else None

    def _welcome_widget(self):
        tabs = self.window.central_tabs
        for index in range(tabs.count()):
            widget = tabs.widget(index)
            if isinstance(widget, WelcomeWidget):
                return widget
        widget = getattr(self.window, "welcome_widget", None)
        if isinstance(widget, WelcomeWidget):
            return widget
        self.window.show_welcome_screen()
        return getattr(self.window, "welcome_widget", None)

    def _focus_capture_setup(self, message):
        self.open_app()
        welcome = self._welcome_widget()
        if welcome is not None:
            index = self.window.central_tabs.indexOf(welcome)
            if index >= 0:
                self.window.central_tabs.setCurrentIndex(index)
            welcome.mic_combo.setFocus()
        self._status(message, error=True)
        return False

    def start_recording(self):
        state = self.snapshot()
        if state["recording_active"]:
            self._status("An audio capture is already active.", error=True)
            return False
        welcome = self._welcome_widget()
        if welcome is None:
            return self._focus_capture_setup("Open the recording setup before starting capture.")
        try:
            settings = QSettings("Hectronic", "Secretario")
            if settings.value("audio_rescan_before_capture", True, type=bool):
                welcome.populate_mics(keep_current=True)
            config = welcome.get_recording_config()
            devices = self.window.recorder.get_input_devices()
            valid_indexes = {int(index) for index, _name in devices}
        except Exception as error:
            return self._focus_capture_setup(f"Could not check the recording device: {error}")

        selected = config.get("device_index")
        needs_microphone = not config.get("capture_system_audio", False)
        if needs_microphone and not devices:
            return self._focus_capture_setup(
                "No microphone is available. Select or connect a device in recording setup."
            )
        if needs_microphone and selected is not None:
            try:
                selected_index = int(selected)
            except (TypeError, ValueError):
                selected_index = -1
            if selected_index not in valid_indexes:
                return self._focus_capture_setup(
                    "The saved microphone is unavailable. Choose an available device in recording setup."
                )

        try:
            widget = self.window.recording_tabs.start_new_recording(config)
        except Exception as error:
            return self._focus_capture_setup(f"Recording could not start: {error}")
        if not widget or not widget.recording_started:
            error = widget.status_label.text() if widget and hasattr(widget, "status_label") else "Recording did not start."
            if widget is not None:
                index = self.window.central_tabs.indexOf(widget)
                if index >= 0:
                    self.window.close_tab(index)
            return self._focus_capture_setup(error)
        self._status("Recording started.")
        return True

    def _current_recording(self):
        _index, widget = self._active_recording()
        return widget

    def toggle_recording_pause(self):
        widget = self._current_recording()
        if widget is None:
            self._stale_action("Recording is no longer active.")
            return False
        widget.toggle_pause()
        self._refresh_menu()
        return True

    def stop_recording(self):
        widget = self._current_recording()
        if widget is not None:
            try:
                widget.finish_recording()
                return True
            except Exception as error:
                self._status(f"Recording could not be saved: {error}", error=True)
                return False
        _index, notebook = self._active_audio_note()
        if notebook is not None:
            try:
                notebook.stop_recording()
                return True
            except Exception as error:
                self._status(f"Audio note could not be saved: {error}", error=True)
                return False
        self._stale_action("Recording is no longer active.")
        return False

    def cancel_recording(self):
        widget = self._current_recording()
        if widget is None:
            self._stale_action("Recording is no longer active.")
            return False
        answer = QMessageBox.question(
            self.window,
            "Cancel recording",
            "Discard this recording? The captured audio will not be saved.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False
        widget.cancel_recording()
        return True

    def open_recording(self):
        index, widget = self._active_recording()
        if index < 0:
            index, widget = self._active_audio_note()
        if index < 0:
            self._stale_action("Recording is no longer active.")
            return False
        self.open_app()
        self.window.central_tabs.setCurrentIndex(index)
        return widget

    def _stale_action(self, message):
        manager = getattr(self.window, "system_tray_manager", None)
        if manager:
            manager.refresh_menu()
        self._status(message, error=True)

    def new_text_note(self):
        note = self.window.open_note_tab()
        if note is None:
            return False
        prepare = getattr(note, "prepare_quick_note", None)
        if callable(prepare):
            prepare()
        index = self.window.central_tabs.indexOf(note)
        if index >= 0:
            self.window.central_tabs.setTabText(index, "Quick Note")
        self.open_app()
        return note

    def new_audio_note(self):
        if self.snapshot()["recording_active"]:
            self._status("Finish the active audio capture before starting an audio note.", error=True)
            return False
        try:
            notebooks = self.window.notebook_db.get_notebooks()
        except Exception as error:
            self._status(f"Notebooks are unavailable: {error}", error=True)
            return False
        if not notebooks:
            self._navigate("open_notebooks_list")
            self._status("Create a notebook before recording an audio note.")
            return False
        if len(notebooks) == 1:
            selected = notebooks[0]
        else:
            names = [item["name"] for item in notebooks]
            name, accepted = QInputDialog.getItem(
                self.window, "New audio note", "Save the voice note in:", names, 0, False
            )
            if not accepted:
                return False
            selected = next(item for item in notebooks if item["name"] == name)
        self.open_app()
        self.window.open_notebook(int(selected["id"]), selected["name"])
        widget = next(
            (self.window.central_tabs.widget(i) for i in range(self.window.central_tabs.count())
             if isinstance(self.window.central_tabs.widget(i), NotebookWidget)
             and self.window.central_tabs.widget(i).notebook_id == int(selected["id"])),
            None,
        )
        if widget is None or getattr(self.window.recorder, "is_recording", False):
            self._status("The audio device is busy. Finish its current capture first.", error=True)
            return False
        try:
            widget.start_recording()
        except Exception as error:
            self._status(f"Audio note could not start: {error}", error=True)
            return False
        if not getattr(self.window.recorder, "is_recording", False):
            self._status("Audio note could not start. Check microphone access and try again.", error=True)
            return False
        self._status("Audio note recording started.")
        return True

    def start_pomodoro(self):
        productivity = getattr(self.window, "productivity", None)
        service = getattr(productivity, "service", None)
        if service is None or not self.snapshot()["pomodoro_can_start"]:
            self._stale_action("A focus session cannot start in the current state.")
            return False
        settings = QSettings("Hectronic", "Secretario")
        minutes = settings.value("pomodoro/focus_minutes", 25, type=int)
        title, accepted = QInputDialog.getText(
            self.window, "Start Pomodoro", "Focus session title:", text="Focus"
        )
        if not accepted:
            return False
        try:
            service.start(title.strip(), planned_seconds=int(minutes) * 60)
        except (RuntimeError, ValueError) as error:
            self._status(str(error), error=True)
            return False
        productivity.refresh_views()
        self._status(f"Focus session started: {title.strip()}.")
        return True

    def toggle_pomodoro(self):
        productivity = getattr(self.window, "productivity", None)
        service = getattr(productivity, "service", None)
        if service is None or service.recovery_required or service.state not in ("running", "paused"):
            self._stale_action("Focus session is no longer active.")
            return False
        (service.pause if service.state == "running" else service.resume)()
        productivity.refresh_views()
        return True

    def finish_pomodoro(self):
        productivity = getattr(self.window, "productivity", None)
        service = getattr(productivity, "service", None)
        if service is None or service.state not in ("running", "paused") or service.recovery_required:
            self._stale_action("Focus session is no longer active.")
            return False
        changed = service.finish()
        productivity.refresh_views()
        self._status("Focus session finished." if changed else "Focus session was already finished.")
        return changed

    def cancel_pomodoro(self):
        productivity = getattr(self.window, "productivity", None)
        service = getattr(productivity, "service", None)
        if service is None or service.state not in ("running", "paused") or service.recovery_required:
            self._stale_action("Focus session is no longer active.")
            return False
        answer = QMessageBox.question(
            self.window, "Cancel Pomodoro", "Cancel this focus session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False
        changed = service.cancel()
        productivity.refresh_views()
        self._status("Focus session cancelled.")
        return changed

    def start_meeting(self, occurrence_id):
        if occurrence_id is None:
            return False
        occurrence = self._meeting_by_id(
            occurrence_id, allowed_states=("scheduled", "notified", "snoozed", "missed")
        )
        if occurrence is None:
            self._stale_action("This meeting is no longer available.")
            return False
        if self.snapshot()["recording_active"]:
            self._status("Finish the active recording before starting this meeting.", error=True)
            return False
        if not self._preflight_meeting_capture():
            return False
        productivity = self.window.productivity
        widget = productivity.start_meeting_occurrence(int(occurrence_id))
        if widget is None or not getattr(widget, "recording_started", False):
            self._status("The prepared meeting recording could not start. Check recording setup.", error=True)
            self._refresh_menu()
            return False
        self._status(f"Meeting recording started: {occurrence['title']}.")
        self._refresh_menu()
        return True

    def _preflight_meeting_capture(self):
        recorder = self.window.recorder
        try:
            devices = recorder.get_input_devices()
        except Exception as error:
            self._focus_capture_setup(f"Could not check the recording device: {error}")
            return False
        if getattr(recorder, "capture_machine_audio", False):
            return True
        if not devices:
            self._focus_capture_setup(
                "No microphone is available. Select or connect a device in recording setup."
            )
            return False
        selected = getattr(recorder, "device_index", None)
        if selected is not None:
            try:
                available = {int(index) for index, _name in devices}
                if int(selected) not in available:
                    self._focus_capture_setup(
                        "The saved microphone is unavailable. Choose an available device in recording setup."
                    )
                    return False
            except (TypeError, ValueError):
                self._focus_capture_setup(
                    "The saved microphone is unavailable. Choose an available device in recording setup."
                )
                return False
        return True

    def snooze_meeting(self, occurrence_id):
        occurrence = self._meeting_by_id(occurrence_id, allowed_states=("notified", "snoozed"))
        if occurrence is None:
            self._stale_action("This meeting reminder is no longer available.")
            return False
        self.window.productivity._snooze_meeting_occurrence(int(occurrence_id), 5)
        return True

    def dismiss_meeting(self, occurrence_id):
        occurrence = self._meeting_by_id(
            occurrence_id, allowed_states=("scheduled", "notified", "snoozed", "missed")
        )
        if occurrence is None:
            self._stale_action("This meeting is no longer available.")
            return False
        self.window.productivity._dismiss_meeting_occurrence(int(occurrence_id))
        return True

    def open_meeting(self, occurrence_id):
        occurrence = self._meeting_by_id(
            occurrence_id, allowed_states=("scheduled", "notified", "snoozed", "started", "missed")
        )
        if occurrence is None:
            self._stale_action("This meeting is no longer available.")
            return False
        self.open_app()
        self.window.productivity.open_meeting_details(int(occurrence_id))
        return True

    def _meeting_by_id(self, occurrence_id, *, allowed_states):
        productivity = getattr(self.window, "productivity", None)
        repository = getattr(getattr(productivity, "meeting_scheduler", None), "repository", None)
        if repository is None:
            return None
        occurrence = repository.get_occurrence(int(occurrence_id))
        if not occurrence or occurrence["state"] not in allowed_states:
            return None
        return occurrence

    def _refresh_menu(self):
        manager = getattr(self.window, "system_tray_manager", None)
        if manager:
            manager.refresh_menu()

    def cleanup(self):
        self._closed = True
