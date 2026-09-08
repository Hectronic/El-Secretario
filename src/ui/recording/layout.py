"""Visual composition for recording detail and audio-edit tabs."""

from PyQt6.QtWidgets import QDoubleSpinBox, QFrame, QGroupBox, QHBoxLayout, QLabel, QVBoxLayout

from src.ui.recording.actions_bar import build_actions_bar
from src.ui.recording.content_tabs import build_content_tabs
from src.ui.recording.controls import create_action_button, create_playback_controls, create_primary_action
from src.ui.recording.metadata_panel import build_metadata_panel
from src.ui.recording.transcription_panel import build_transcription_panel

def init_ui(widget):
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(10, 10, 10, 10)

    if widget.audio_edit_mode:
        widget._build_audio_editor_ui(layout)
        return

    widget._build_transcription_controls(layout)
    widget._build_playback_controls(layout)
    widget._build_separator(layout)
    widget._build_metadata_panel(layout)
    widget._build_content_tabs(layout)
    widget._build_bottom_actions(layout)



def _build_transcription_controls(widget, layout):
    panel = build_transcription_panel(widget, widget.retranscribe_recording)
    widget.model_combo = panel.model_combo
    widget.lang_combo = panel.lang_combo
    widget.diarization_check = panel.diarization_check
    widget.retranscribe_btn = panel.retranscribe_btn
    layout.addLayout(panel.layout)



def _build_playback_controls(widget, layout):
    playback_controls = create_playback_controls(
        widget,
        on_play=widget.play_audio,
        on_pause=widget.pause_audio,
        on_stop=widget.stop_audio,
        on_slider_moved=widget.set_position,
        on_volume_changed=widget.audio_output.setVolume,
    )
    playback_layout = playback_controls.layout
    widget.play_btn = playback_controls.play_btn
    widget.pause_btn = playback_controls.pause_btn
    widget.stop_btn = playback_controls.stop_btn
    widget.slider = playback_controls.slider
    widget.time_label = playback_controls.time_label
    widget.volume_slider = playback_controls.volume_slider

    widget.edit_audio_btn = create_primary_action(
        "Edit Audio in New Tab",
        widget.open_audio_editor,
        min_height=38,
        enabled=False,
        parent=widget,
    )
    playback_layout.insertWidget(3, widget.edit_audio_btn)
    layout.addLayout(playback_layout)

    widget.audio_edit_group = None
    widget.trim_start_spin = None
    widget.trim_end_spin = None
    widget.mark_start_btn = None
    widget.mark_end_btn = None
    widget.trim_btn = None



def _build_separator(widget, layout):
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    layout.addWidget(line)



def _build_metadata_panel(widget, layout):
    panel = build_metadata_panel(widget.db.get_all_tags())
    widget.title_input = panel.title_input
    widget.date_label = panel.date_label
    widget.duration_label = panel.duration_label
    widget.tags_input = panel.tags_input
    widget.is_diarized_check_meta = panel.is_diarized_check
    layout.addWidget(panel.group)



def _build_content_tabs(widget, layout):
    panel = build_content_tabs(
        widget,
        widget.db,
        widget.current_record_id,
        open_speaker_manager=widget.open_speaker_manager,
        copy_transcription=widget.copy_transcription_to_clipboard,
        on_transcription_text_changed=widget._update_transcription_actions,
    )
    widget.tabs = panel.tabs
    widget.text_display = panel.text_display
    widget.notes_display = panel.notes_display
    widget.summary_display = panel.summary_display
    widget.tasks_widget = panel.tasks_widget
    widget.rename_speakers_btn = panel.rename_speakers_btn
    widget.copy_transcription_btn = panel.copy_transcription_btn
    layout.addWidget(panel.tabs)



def _build_bottom_actions(widget, layout):
    actions = build_actions_bar(
        widget,
        summarize_slot=lambda: widget.run_ai_task("summary"),
        extract_tasks_slot=lambda: widget.run_ai_task("task_extraction"),
        save_slot=widget.save_all_changes,
        ask_slot=widget.open_chat_for_recording,
        delete_slot=widget.delete_recording,
    )
    widget.summarize_btn = actions.summarize_btn
    widget.extract_tasks_btn = actions.extract_tasks_btn
    widget.save_all_btn = actions.save_all_btn
    widget.ask_meeting_btn = actions.ask_meeting_btn
    widget.delete_btn = actions.delete_btn
    layout.addLayout(actions.layout)



def _build_audio_editor_ui(widget, layout):
    playback_controls = create_playback_controls(
        widget,
        on_play=widget.play_audio,
        on_pause=widget.pause_audio,
        on_stop=widget.stop_audio,
        on_slider_moved=widget.set_position,
        on_volume_changed=widget.audio_output.setVolume,
    )
    widget.play_btn = playback_controls.play_btn
    widget.pause_btn = playback_controls.pause_btn
    widget.stop_btn = playback_controls.stop_btn
    widget.slider = playback_controls.slider
    widget.time_label = playback_controls.time_label
    widget.volume_slider = playback_controls.volume_slider
    layout.addLayout(playback_controls.layout)

    edit_group = QGroupBox("Audio Edit")
    edit_layout = QVBoxLayout(edit_group)
    edit_layout.setSpacing(8)

    edit_row = QHBoxLayout()
    widget.trim_start_spin = QDoubleSpinBox()
    widget.trim_start_spin.setDecimals(2)
    widget.trim_start_spin.setSingleStep(0.5)
    widget.trim_start_spin.setMinimum(0.0)
    widget.trim_start_spin.setMaximum(0.0)
    widget.trim_start_spin.setSuffix(" s")
    edit_row.addWidget(QLabel("Start:"))
    edit_row.addWidget(widget.trim_start_spin)

    widget.trim_end_spin = QDoubleSpinBox()
    widget.trim_end_spin.setDecimals(2)
    widget.trim_end_spin.setSingleStep(0.5)
    widget.trim_end_spin.setMinimum(0.0)
    widget.trim_end_spin.setMaximum(0.0)
    widget.trim_end_spin.setSuffix(" s")
    edit_row.addWidget(QLabel("End:"))
    edit_row.addWidget(widget.trim_end_spin)

    widget.mark_start_btn = create_action_button(
        "Mark Start",
        widget.mark_trim_start_from_playhead,
        parent=widget,
    )
    edit_row.addWidget(widget.mark_start_btn)

    widget.mark_end_btn = create_action_button(
        "Mark End",
        widget.mark_trim_end_from_playhead,
        parent=widget,
    )
    edit_row.addWidget(widget.mark_end_btn)
    edit_row.addStretch()
    edit_layout.addLayout(edit_row)

    trim_row = QHBoxLayout()
    widget.trim_btn = create_primary_action(
        "Trim and Retranscribe",
        widget.trim_audio_selection,
        parent=widget,
    )
    trim_row.addWidget(widget.trim_btn)
    trim_row.addStretch()
    edit_layout.addLayout(trim_row)

    layout.addWidget(edit_group)
    widget.audio_edit_group = edit_group

    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    layout.addWidget(line)

    widget.duration_label = None
    widget.model_combo = None
    widget.lang_combo = None
    widget.diarization_check = None
    widget.title_input = None
    widget.save_all_btn = None
    widget.date_label = None
    widget.duration_label = None
    widget.tags_input = None
    widget.is_diarized_check_meta = None
    widget.tabs = None
    widget.text_display = None
    widget.notes_display = None
    widget.summary_display = None
    widget.tasks_widget = None
    widget.summarize_btn = None
    widget.extract_tasks_btn = None
    widget.retranscribe_btn = None
    widget.ask_meeting_btn = None
    widget.delete_btn = None
    widget.rename_speakers_btn = None
    widget.copy_transcription_btn = None
    return
