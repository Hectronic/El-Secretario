"""Canonical setting descriptors shared by Settings navigation and search."""

from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlparse

from PyQt6.QtWidgets import QCheckBox, QComboBox, QLineEdit, QSpinBox, QTextEdit

from src.transcription_options import (
    DEFAULT_TRANSCRIPTION_MODEL,
    get_sherpa_model_type_options,
    get_transcription_model_options,
)
from src.ui.settings.prompts_defaults import DEFAULT_PROMPTS
from src.worker_components.sherpa import default_sherpa_model_url


CATEGORIES = (
    "Appearance & language",
    "Recording & devices",
    "Transcription & speakers",
    "AI & chat",
    "Search & knowledge",
    "Automation & notifications",
    "Integrations",
)

CATEGORY_SUMMARIES = {
    "Appearance & language": "Theme and language used for generated summaries.",
    "Recording & devices": "Input devices, recording capture, and recording safety.",
    "Transcription & speakers": "Models, runtime, compute policy, and diarization access.",
    "AI & chat": "Provider connections, models, and prompt templates.",
    "Search & knowledge": "Indexing, RAG runtime options, and explicit maintenance actions.",
    "Automation & notifications": "Startup summaries, recording reminders, and updates.",
    "Integrations": "Local API, MCP, and operating-system integration actions.",
}


def _url(value):
    parsed = urlparse(str(value).strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return "Enter a complete HTTP or HTTPS URL."
    return ""


def _nonempty(value):
    return "This value cannot be empty." if not str(value).strip() else ""


def _choice(options):
    allowed = set(options)
    return lambda value: "Choose one of the listed options." if value not in allowed else ""


def _prompt(required):
    def validate(value):
        missing = [placeholder for placeholder in required if placeholder not in str(value)]
        return "Keep the required placeholder(s): " + ", ".join(missing) + "." if missing else ""
    return validate


@dataclass
class SettingDescriptor:
    keys: tuple[str, ...]
    label: str
    help: str
    category: str
    default: object
    control: object
    view: object = None
    advanced: bool = False
    synonyms: tuple[str, ...] = ()
    timing: str = "Takes effect on the next job."
    validator: Callable | None = None
    owner: object = None
    row_label: object = None
    wrapper: object = None
    error_label: object = None

    def __post_init__(self):
        self.view = self.view or self.control
        if isinstance(self.keys, str):
            self.keys = (self.keys,)

    @property
    def key(self):
        return self.keys[0]

    def search_text(self):
        return " ".join((self.label, self.help, self.category, *self.synonyms)).casefold()

    def reset(self):
        value = self.default
        control = self.control
        if self.key in {"default_mic_name", "ai_provider"}:
            control.setCurrentIndex(0)
            return
        if self.key == "ollama_model":
            control.setCurrentIndex(-1)
            control.setProperty("settingsClearOnSave", True)
            return
        if self.key == "recording_guardian/duration_reminder_seconds":
            control.setValue(int(value) // 60)
            return
        if self.key == "recording_guardian/silence_warning_seconds":
            control.setValue(int(value) // 60)
            return
        if isinstance(control, QCheckBox):
            control.setChecked(bool(value))
        elif isinstance(control, QComboBox):
            control.setCurrentText(str(value))
        elif isinstance(control, QLineEdit):
            control.setText(str(value if value is not None else ""))
        elif isinstance(control, QTextEdit):
            control.setPlainText(str(value if value is not None else ""))
        elif isinstance(control, QSpinBox):
            control.setValue(int(value))


def build_setting_catalog(widget):
    """Describe each existing editable Settings field exactly once."""
    g, a, r, p, productivity = (
        widget.general_panel,
        widget.audio_panel,
        widget.rag_panel,
        widget.prompts_panel,
        widget.productivity_panel,
    )
    models = get_transcription_model_options()
    sherpa_types = get_sherpa_model_type_options()
    gemini_models = [g.gemini_model_combo.itemText(i) for i in range(g.gemini_model_combo.count())]
    fields = []

    def add(key, label, help_text, category, default, control, *, view=None,
            advanced=False, synonyms=(), timing="Takes effect on the next job.",
            validator=None, owner=None):
        fields.append(SettingDescriptor(
            (key,) if isinstance(key, str) else tuple(key), label, help_text,
            category, default, control, view, advanced, tuple(synonyms),
            timing, validator, owner,
        ))

    add("app_theme", "Interface theme", "Choose system colors or a built-in theme.",
        "Appearance & language", "System", g.theme_combo, advanced=False,
        synonyms=("appearance", "dark mode", "light mode"), timing="Applied immediately.",
        validator=_choice(["System", "Light", "Dark", "SNES"]), owner=g)
    add("system_language", "Summary language", "Language used for AI generated daily and weekly summaries.",
        "Appearance & language", "Spanish", g.lang_input, synonyms=("idioma", "language", "summary"),
        validator=_nonempty, owner=g)

    add(("default_mic_name", "default_mic_index"), "Default microphone",
        "Select an input device or use the system default.", "Recording & devices",
        ("", None), a.mic_combo, view=a.mic_combo.parentWidget(), advanced=False,
        synonyms=("microphone", "mic", "input device", "micrófono"), timing="Used by the next capture.", owner=a)
    add("capture_system_audio", "System audio capture", "Record audio playing through the machine's output device.",
        "Recording & devices", False, a.sys_audio_check, synonyms=("loopback", "speaker", "desktop audio"),
        timing="Used by the next capture.", owner=a)
    add("recording_guardian/duration_reminder_seconds", "Active recording reminder",
        "Minutes between reminders while a recording is active.", "Recording & devices", 3600,
        a.duration_reminder_spin, advanced=False, synonyms=("recording safety", "reminder"),
        validator=lambda v: "Choose a duration from 60 to 86400 seconds." if not 60 <= int(v) <= 86400 else "", owner=a)
    add("recording_guardian/duration_reminders_enabled", "Duration reminders",
        "Show reminders during long recordings.", "Recording & devices", True,
        a.duration_reminders_enabled_check, owner=a)
    add("recording_guardian/silence_warning_seconds", "No-audio warning",
        "Minutes without detected audio before a warning.", "Recording & devices", 900,
        a.silence_warning_spin, advanced=False, synonyms=("silence", "recording safety"),
        validator=lambda v: "Choose a duration from 60 to 86400 seconds." if not 60 <= int(v) <= 86400 else "", owner=a)
    add("recording_guardian/silence_warnings_enabled", "Silence warnings",
        "Warn when an active recording receives no audio.", "Recording & devices", True,
        a.silence_warnings_enabled_check, owner=a)
    add("recording_guardian/tray_notifications_enabled", "Safety notifications",
        "Show recording safety notifications through the system tray.", "Recording & devices", True,
        a.tray_notifications_enabled_check, advanced=True, synonyms=("tray", "notifications"), owner=a)
    add("recording_guardian/auto_stop_after_silence", "Automatic silence stop",
        "Stop and save after the no-audio warning.", "Recording & devices", False,
        a.auto_stop_silence_check, advanced=True, synonyms=("silence", "safety"), owner=a)
    add("audio_rescan_before_capture", "Re-scan devices before capture",
        "Refresh audio inputs before recording or importing audio.", "Recording & devices", True,
        a.rescan_before_capture_check, advanced=True, synonyms=("USB", "device detection"), owner=a)
    add("audio_prefer_device_index", "Prefer microphone index",
        "Match the saved device index before its name when device names are duplicated.",
        "Recording & devices", False, a.prefer_index_check, advanced=True,
        synonyms=("device matching", "USB"), owner=a)

    add("whisper_model", "Default transcription model", "Model used for new transcription jobs.",
        "Transcription & speakers", DEFAULT_TRANSCRIPTION_MODEL, a.whisper_combo,
        advanced=False, synonyms=("speech to text", "STT", "model"),
        validator=_choice(models), owner=a)
    add("sherpa_onnx_model_dir", "Sherpa model directory", "Local directory containing Sherpa ONNX model files.",
        "Transcription & speakers", "models/sherpa-onnx", a.sherpa_model_dir_input,
        advanced=True, synonyms=("path", "local model"), validator=_nonempty, owner=a)
    add("sherpa_onnx_model_type", "Sherpa model type", "Model architecture loaded by Sherpa ONNX.",
        "Transcription & speakers", "auto", a.sherpa_model_type_combo, advanced=True,
        synonyms=("architecture",), validator=_choice(sherpa_types), owner=a)
    add("sherpa_onnx_auto_download", "Download missing Sherpa model",
        "Download the default archive if local model files are missing.",
        "Transcription & speakers", True, a.sherpa_auto_download_check, advanced=True, owner=a)
    add("sherpa_onnx_model_url", "Sherpa model URL", "Archive URL used for automatic model download.",
        "Transcription & speakers", default_sherpa_model_url(), a.sherpa_model_url_input,
        advanced=True, synonyms=("download", "URL"), validator=_url, owner=a)
    add("hf_token", "Hugging Face token", "Access token needed for speaker diarization models.",
        "Transcription & speakers", "", g.token_input, view=g.hf_container, advanced=True,
        synonyms=("speaker diarization", "token", "credential", "GPU", "CUDA"), owner=g)
    add("force_cpu", "Force CPU", "Disable GPU acceleration for transcription and diarization.",
        "Transcription & speakers", False, a.force_cpu_check, advanced=True,
        synonyms=("GPU", "CUDA", "processor"), owner=a)
    add("compute_type", "Compute precision", "Precision used by the transcription runtime.",
        "Transcription & speakers", "auto", a.compute_combo, advanced=True,
        synonyms=("GPU", "CUDA", "float16", "int8"), validator=_choice(["auto", "int8", "int8_float16", "float16", "float32"]), owner=a)
    add("transcription_backend", "Transcription backend", "Backend used to run speech recognition.",
        "Transcription & speakers", "auto", a.backend_combo, advanced=True,
        synonyms=("STT", "speech to text", "faster whisper"),
        validator=_choice(["auto", "faster-whisper", "openai-whisper"]), owner=a)

    add("ai_provider", "AI provider", "Choose the cloud Gemini provider or local Ollama.",
        "AI & chat", "gemini", g.provider_combo, synonyms=("LLM", "chat", "model"),
        validator=_choice(["gemini", "ollama"]), owner=g)
    add("gemini_key", "Gemini API key", "Credential used to access Google Gemini.",
        "AI & chat", "", g.gemini_key_input, view=g.gemini_container, advanced=False,
        synonyms=("Google", "API key", "credential"), owner=g)
    add("gemini_model", "Gemini model", "Model used for Gemini requests.",
        "AI & chat", "gemini-3-flash-preview", g.gemini_model_combo, advanced=True,
        synonyms=("Google", "LLM"), validator=_choice(gemini_models), owner=g)
    add("ollama_host", "Ollama server", "HTTP address of the local Ollama server.",
        "AI & chat", "http://localhost:11434", g.ollama_host_input, advanced=False,
        synonyms=("local AI", "host", "URL"), validator=_url, owner=g)
    add("ollama_model", "Ollama model", "Local model name served by Ollama.",
        "AI & chat", "", g.ollama_model_combo, advanced=False,
        synonyms=("local AI", "LLM"), validator=lambda v: "Choose an Ollama model." if not str(v).strip() else "", owner=g)
    prompt_info = {
        "summary": ("Recording summary prompt", "Used to summarize one transcription.", ("{text}",)),
        "clean": ("Clean transcription prompt", "Used to edit a transcription without summarizing it.", ("{text}",)),
        "daily_summary": ("Daily summary prompt", "Used to summarize recording summaries for one day.", ("{text}", "{language}")),
        "weekly_summary": ("Weekly summary prompt", "Used to summarize the current week's recordings.", ("{text}", "{language}")),
        "task_extraction": ("Task extraction prompt", "Used to extract actionable tasks as JSON.", ("{text}", "{language}")),
    }
    for key, (label, help_text, placeholders) in prompt_info.items():
        add("prompt_" + key, label, help_text, "AI & chat", DEFAULT_PROMPTS[key],
            p.prompt_editors[key], advanced=True, synonyms=("prompt", "template", "instructions"),
            validator=_prompt(placeholders), owner=p)

    add("auto_index_rag", "Automatically index new content", "Index new or updated notes and transcriptions for search.",
        "Search & knowledge", True, a.rag_auto_index_check, advanced=False,
        synonyms=("RAG", "vector search", "indexing"), owner=a)
    add("rag_enabled", "Enable semantic search", "Make RAG search and chat available.",
        "Search & knowledge", True, r.rag_enabled_check, advanced=False,
        synonyms=("RAG", "knowledge", "vector search"), timing="Used after RAG initialize or reload.", owner=r)
    add("rag_persist_directory", "Vector database directory", "Directory where the RAG index is stored.",
        "Search & knowledge", "chroma_db", r.persist_dir_input, advanced=True,
        synonyms=("RAG", "index path", "storage"), validator=_nonempty, timing="Used after RAG initialize or reload.", owner=r)
    add("rag_safe_delete_mode", "Safe delete mode", "Use the platform-safe delete path for vector data.",
        "Search & knowledge", True, r.safe_delete_check, advanced=True,
        synonyms=("RAG", "Windows"), timing="Used after RAG initialize or reload.", owner=r)
    add("rag_subprocess_upsert_mode", "Subprocess indexing", "Run RAG upserts in a subprocess.",
        "Search & knowledge", True, r.subprocess_upsert_check, advanced=True,
        synonyms=("RAG", "index"), timing="Used after RAG initialize or reload.", owner=r)
    add("rag_subprocess_query_mode", "Subprocess search", "Run RAG queries in a subprocess.",
        "Search & knowledge", True, r.subprocess_query_check, advanced=True,
        synonyms=("RAG", "query"), timing="Used after RAG initialize or reload.", owner=r)

    add("startup_enqueue_last_weekly_summary", "Create missing weekly summary on startup",
        "Queue the previous week's summary when it does not exist.", "Automation & notifications",
        False, g.startup_last_weekly_check, advanced=False, synonyms=("automation", "weekly"),
        timing="Used on next application start.", owner=g)
    add("startup_enqueue_previous_daily_summary", "Create missing daily summary on startup",
        "Queue the latest earlier day that has recordings but no summary.", "Automation & notifications",
        False, g.startup_prev_daily_check, advanced=False, synonyms=("automation", "daily"),
        timing="Used on next application start.", owner=g)
    add("enable_auto_update", "Check for updates on startup", "Check for a new version when the app starts.",
        "Automation & notifications", True, g.enable_update_check, advanced=True,
        synonyms=("update", "upgrade"), timing="Restart required.", owner=g)
    add("pomodoro/focus_minutes", "Default Pomodoro focus duration",
        "Length of a new focus interval.", "Automation & notifications", 25,
        productivity.focus_minutes, advanced=False, synonyms=("timer", "pomodoro", "focus"),
        timing="Used for the next focus interval.",
        validator=lambda v: "Choose 1–240 minutes." if not 1 <= int(v) <= 240 else "", owner=productivity)
    add("pomodoro/short_break_minutes", "Default short break duration",
        "Length of a new short break.", "Automation & notifications", 5,
        productivity.short_break_minutes, advanced=False, synonyms=("timer", "pomodoro", "break"),
        timing="Used for the next short break.",
        validator=lambda v: "Choose 1–240 minutes." if not 1 <= int(v) <= 240 else "", owner=productivity)
    add("pomodoro/long_break_minutes", "Default long break duration",
        "Length of a new long break.", "Automation & notifications", 15,
        productivity.long_break_minutes, advanced=False, synonyms=("timer", "pomodoro", "break"),
        timing="Used for the next long break.",
        validator=lambda v: "Choose 1–240 minutes." if not 1 <= int(v) <= 240 else "", owner=productivity)
    add("pomodoro/tray_notifications", "Pomodoro completion notifications",
        "Show a system tray notification when a focus interval completes.",
        "Automation & notifications", True, productivity.tray_notifications,
        advanced=False, synonyms=("pomodoro", "tray", "notification"),
        timing="Used for the next completion.", owner=productivity)

    add("enable_local_api", "Local REST API", "Allow local clients to use the loopback-only API.",
        "Integrations", False, g.enable_local_api_check, advanced=False,
        synonyms=("REST", "localhost", "127.0.0.1"), timing="Applied immediately.", owner=g)
    add("enable_mcp_server", "MCP server", "Allow compatible local AI clients to connect through MCP.",
        "Integrations", False, g.enable_mcp_server_check, advanced=True,
        synonyms=("Model Context Protocol", "Claude"), timing="Restart required.", owner=g)
    return fields


def effective_defaults(catalog):
    defaults = {}
    for field in catalog:
        if len(field.keys) == 2:
            defaults.update(zip(field.keys, field.default))
        else:
            defaults[field.key] = field.default
    return defaults
