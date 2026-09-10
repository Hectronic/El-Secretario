"""Qt composition for the waveform audio editor."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSlider,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from src.ui.audio_editor.waveform import AudioWaveformWidget


def build_audio_editor_layout(editor):
    """Create editor controls and wire them to the public widget actions."""
    layout = QVBoxLayout(editor)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(8)
    editor.setStyleSheet("QLabel#editorMeta { font-size: 12px; }")

    header = QHBoxLayout()
    editor.title_label = QLabel("Audio Editor")
    editor.title_label.setStyleSheet("font-size: 16px; font-weight: 700;")
    header.addWidget(editor.title_label)
    editor.file_info_label = QLabel("No audio loaded")
    editor.file_info_label.setObjectName("editorMeta")
    header.addWidget(editor.file_info_label)
    header.addStretch()
    editor.hint_label = QLabel("Drag segment edges on the waveform to retime cuts")
    editor.hint_label.setObjectName("editorMeta")
    header.addWidget(editor.hint_label)
    layout.addLayout(header)

    playback_frame = QFrame()
    playback_frame.setFrameShape(QFrame.Shape.StyledPanel)
    playback = QHBoxLayout(playback_frame)
    editor.play_btn = _media_button(editor, QStyle.StandardPixmap.SP_MediaPlay, "Play", editor.play_audio)
    editor.pause_btn = _media_button(editor, QStyle.StandardPixmap.SP_MediaPause, "Pause", editor.pause_audio)
    editor.stop_btn = _media_button(editor, QStyle.StandardPixmap.SP_MediaStop, "Stop", editor.stop_audio)
    playback.addWidget(editor.play_btn)
    playback.addWidget(editor.pause_btn)
    playback.addWidget(editor.stop_btn)
    editor.slider = QSlider(Qt.Orientation.Horizontal)
    editor.slider.setRange(0, 0)
    editor.slider.sliderMoved.connect(editor.set_position)
    playback.addWidget(editor.slider)
    editor.time_label = QLabel("00:00 / 00:00")
    playback.addWidget(editor.time_label)
    playback.addWidget(QLabel("Vol"))
    editor.volume_slider = QSlider(Qt.Orientation.Horizontal)
    editor.volume_slider.setRange(0, 100)
    editor.volume_slider.setValue(70)
    editor.volume_slider.setFixedWidth(80)
    editor.volume_slider.valueChanged.connect(editor.audio_output.setVolume)
    playback.addWidget(editor.volume_slider)
    layout.addWidget(playback_frame)

    editor.waveform = AudioWaveformWidget()
    editor.waveform.selection_changed.connect(editor._on_waveform_selection_changed)
    editor.waveform.chunk_clicked.connect(editor._on_waveform_chunk_clicked)
    editor.waveform.seek_requested.connect(editor._seek_to_time)
    editor.waveform.boundary_dragged.connect(editor._on_waveform_boundary_dragged)
    editor.waveform.boundary_drag_started.connect(editor._on_boundary_drag_started)
    editor.waveform.boundary_drag_finished.connect(editor._on_boundary_drag_finished)
    editor.waveform.setMinimumHeight(320)
    layout.addWidget(editor.waveform, 1)

    tools = QWidget()
    tools_layout = QHBoxLayout(tools)
    selection = QGroupBox("Selection")
    selection_layout = QVBoxLayout(selection)
    row = QHBoxLayout()
    editor.selection_start_spin = _selection_spin(editor._on_spin_selection_changed)
    editor.selection_end_spin = _selection_spin(editor._on_spin_selection_changed)
    row.addWidget(QLabel("Start:"))
    row.addWidget(editor.selection_start_spin)
    row.addWidget(QLabel("End:"))
    row.addWidget(editor.selection_end_spin)
    selection_layout.addLayout(row)
    selection_actions = QHBoxLayout()
    for name, action in (("Mark Start", editor.mark_start_from_playhead), ("Mark End", editor.mark_end_from_playhead), ("Split", editor.split_selection), ("Cut", editor.cut_selection)):
        button = QPushButton(name)
        button.clicked.connect(action)
        selection_actions.addWidget(button)
        setattr(editor, {"Mark Start": "mark_start_btn", "Mark End": "mark_end_btn", "Split": "split_btn", "Cut": "cut_btn"}[name], button)
    selection_layout.addLayout(selection_actions)
    tools_layout.addWidget(selection, 2)

    chunks = QGroupBox("Chunks")
    chunks_layout = QVBoxLayout(chunks)
    editor.chunk_list = QListWidget()
    editor.chunk_list.setMaximumHeight(160)
    editor.chunk_list.currentRowChanged.connect(editor._on_chunk_row_changed)
    chunks_layout.addWidget(editor.chunk_list)
    chunk_actions = QHBoxLayout()
    for name, action, attribute in (("Up", lambda: editor.move_chunk(-1), "up_btn"), ("Down", lambda: editor.move_chunk(1), "down_btn"), ("Delete", editor.delete_chunk, "delete_chunk_btn"), ("Reset", editor.reset_edits, "reset_btn")):
        button = QPushButton(name)
        button.clicked.connect(action)
        chunk_actions.addWidget(button)
        setattr(editor, attribute, button)
    chunks_layout.addLayout(chunk_actions)
    tools_layout.addWidget(chunks, 3)
    layout.addWidget(tools)

    actions = QHBoxLayout()
    editor.apply_btn = QPushButton("Apply Edits")
    editor.apply_btn.setProperty("class", "calendar-primary-btn")
    editor.apply_btn.setMinimumHeight(34)
    editor.apply_btn.clicked.connect(editor.apply_edits)
    actions.addWidget(editor.apply_btn)
    actions.addStretch()
    layout.addLayout(actions)
    editor.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), editor)
    editor.undo_shortcut.activated.connect(editor.undo)
    editor.redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), editor)
    editor.redo_shortcut.activated.connect(editor.redo)
    editor.redo_alt_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Z"), editor)
    editor.redo_alt_shortcut.activated.connect(editor.redo)


def _media_button(editor, icon, tooltip, action):
    button = QPushButton()
    button.setIcon(editor.style().standardIcon(icon))
    button.setToolTip(tooltip)
    button.setEnabled(False)
    button.clicked.connect(action)
    return button


def _selection_spin(action):
    spin = QDoubleSpinBox()
    spin.setDecimals(3)
    spin.setSingleStep(0.1)
    spin.setMinimum(0.0)
    spin.valueChanged.connect(action)
    return spin
