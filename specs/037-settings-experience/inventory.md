# SPEC-037 settings inventory

This inventory is the pre-migration map for controls owned by the Settings
window. Defaults and normalization are taken from the existing panels and their
runtime consumers. Settings outside that window are listed separately below.

## Settings window controls

| Category / control | QSettings key | Default | Validation / reset | Consumer and when it takes effect |
| --- | --- | --- | --- | --- |
| Appearance & language / Theme | `app_theme` | `System` | `System`, `Light`, `Dark`, `SNES` | `src/ui/styles.py`; immediate |
| Appearance & language / Summary language | `system_language` | `Spanish` | Non-empty text | `src/ai_assistant.py`, summary generation; next summary |
| Recording & devices / Microphone | `default_mic_name`, `default_mic_index` | `""`, system default (`None`) | Current scanned device or system default | `src/ui/welcome/capture_state.py`, Pomodoro device selection; next capture |
| Recording & devices / System audio | `capture_system_audio` | `False` | Boolean | Welcome capture defaults; next capture |
| Recording & devices / Recording reminder interval | `recording_guardian/duration_reminder_seconds` | `3600` | 1–1440 minutes; persisted as seconds | Recording guardian; next recording |
| Recording & devices / Reminder enabled | `recording_guardian/duration_reminders_enabled` | `True` | Boolean | Recording guardian; next recording |
| Recording & devices / Silence warning interval | `recording_guardian/silence_warning_seconds` | `900` | 1–1440 minutes; persisted as seconds | Recording guardian; next recording |
| Recording & devices / Silence warning enabled | `recording_guardian/silence_warnings_enabled` | `True` | Boolean | Recording guardian; next recording |
| Recording & devices / Tray safety notifications | `recording_guardian/tray_notifications_enabled` | `True` | Boolean | Recording guardian; next recording |
| Recording & devices / Stop after silence | `recording_guardian/auto_stop_after_silence` | `False` | Boolean | Recording guardian; next recording |
| Recording & devices / Rescan before capture | `audio_rescan_before_capture` | `True` | Boolean | Capture runtime; next capture |
| Recording & devices / Prefer saved device index | `audio_prefer_device_index` | `False` | Boolean | Capture and Pomodoro device matching; next capture |
| Transcription & speakers / Default transcription model | `whisper_model` | `DEFAULT_TRANSCRIPTION_MODEL` | Must be a listed model | Recording/transcription runtime; next job |
| Transcription & speakers / Sherpa model directory | `sherpa_onnx_model_dir` | `models/sherpa-onnx` | Non-empty path | Sherpa model manager; next Sherpa job |
| Transcription & speakers / Sherpa model type | `sherpa_onnx_model_type` | `auto` | Supported Sherpa type | Sherpa model manager; next Sherpa job |
| Transcription & speakers / Sherpa auto-download | `sherpa_onnx_auto_download` | `True` | Boolean | Sherpa model manager; next Sherpa job |
| Transcription & speakers / Sherpa model URL | `sherpa_onnx_model_url` | `default_sherpa_model_url()` | HTTP(S) URL | Sherpa model manager; next model download |
| Transcription & speakers / Hugging Face token | `hf_token` | empty | Optional secret; masked | Diarization worker; next job |
| Transcription & speakers / Force CPU | `force_cpu` | `False` | Boolean | STT and diarization runtime; next job |
| Transcription & speakers / Compute type | `compute_type` | `auto` | `auto`, `int8`, `int8_float16`, `float16`, `float32` | STT and diarization runtime; next job |
| Transcription & speakers / Backend | `transcription_backend` | `auto` | `auto`, `faster-whisper`, `openai-whisper` | Transcription runtime; next job |
| AI & chat / Provider | `ai_provider` | `gemini` | `gemini`, `ollama` | Provider factory; next request |
| AI & chat / Gemini key | `gemini_key` | empty | Optional secret; masked | Gemini provider; next request |
| AI & chat / Gemini model | `gemini_model` | `gemini-3-flash-preview` | Must be a listed model | Gemini provider; next request |
| AI & chat / Ollama host | `ollama_host` | `http://localhost:11434` | HTTP(S) URL with host | Ollama provider; next request |
| AI & chat / Ollama model | `ollama_model` | empty | Non-empty when provider is Ollama | Ollama provider; next request |
| AI & chat / Recording summary prompt | `prompt_summary` | `DEFAULT_PROMPTS[summary]` | Must retain `{text}` | Summary generation; next summary |
| AI & chat / Clean transcription prompt | `prompt_clean` | `DEFAULT_PROMPTS[clean]` | Must retain `{text}` | AI assistant; next clean request |
| AI & chat / Daily summary prompt | `prompt_daily_summary` | `DEFAULT_PROMPTS[daily_summary]` | Must retain `{text}` and `{language}` | Summary generation; next summary |
| AI & chat / Weekly summary prompt | `prompt_weekly_summary` | `DEFAULT_PROMPTS[weekly_summary]` | Must retain `{text}` and `{language}` | Summary generation; next summary |
| AI & chat / Task extraction prompt | `prompt_task_extraction` | `DEFAULT_PROMPTS[task_extraction]` | Must retain `{text}` and `{language}` | AI assistant; next extraction |
| Search & knowledge / Auto-index | `auto_index_rag` | `True` | Boolean | Note/transcription indexing; next saved content |
| Search & knowledge / RAG enabled | `rag_enabled` | `True` | Boolean | Main-window RAG startup/reload; next initialize/reload |
| Search & knowledge / RAG directory | `rag_persist_directory` | `chroma_db` | Non-empty path | RAG runtime; next initialize/reload |
| Search & knowledge / Safe delete | `rag_safe_delete_mode` | `True` | Boolean | RAG runtime; next initialize/reload |
| Search & knowledge / Subprocess upsert | `rag_subprocess_upsert_mode` | `True` | Boolean | RAG runtime; next initialize/reload |
| Search & knowledge / Subprocess query | `rag_subprocess_query_mode` | `True` | Boolean | RAG runtime; next initialize/reload |
| Automation & notifications / Startup weekly summary | `startup_enqueue_last_weekly_summary` | `False` | Boolean | Startup coordinator; next application start |
| Automation & notifications / Startup daily summary | `startup_enqueue_previous_daily_summary` | `False` | Boolean | Startup coordinator; next application start |
| Automation & notifications / Automatic updates | `enable_auto_update` | `True` | Boolean | Updater startup; restart required |
| Automation & notifications / Pomodoro focus duration | `pomodoro/focus_minutes` | `25` minutes | 1–240 minutes | Pomodoro widget/service; next focus interval |
| Automation & notifications / Pomodoro short break | `pomodoro/short_break_minutes` | `5` minutes | 1–240 minutes | Pomodoro widget/service; next short break |
| Automation & notifications / Pomodoro long break | `pomodoro/long_break_minutes` | `15` minutes | 1–240 minutes | Pomodoro widget/service; next long break |
| Automation & notifications / Pomodoro completion notification | `pomodoro/tray_notifications` | `True` | Boolean | Main-window productivity coordinator; next completion |
| Integrations / Local REST API | `enable_local_api` | `False` | Boolean | Main-window API; immediate |
| Integrations / MCP server | `enable_mcp_server` | `False` | Boolean | MCP server bootstrap; restart required |

The two microphone keys are one control and one reset operation. Existing
normalization remains intact: microphone defaults are represented by an empty
name and `None` index; recording intervals are displayed as minutes and stored
in seconds; model-type helpers normalize legacy Sherpa values.

## Existing actions

| Action | Canonical category | Persistence / side effect |
| --- | --- | --- |
| Re-scan microphone devices | Recording & devices | Reads audio hardware; never changes the saved selection by itself |
| Refresh Ollama models | AI & chat | Network read only; does not save or change provider settings |
| Check for updates | Automation & notifications | Network action; existing safe restart flow remains owner |
| Repair desktop/app shortcuts | Integrations | Runs the existing platform installer action |
| Copy Claude Desktop config | Integrations | Explicit clipboard action; generated config contains no credentials |
| Initialize RAG | Search & knowledge | Explicitly saves valid RAG edits, then emits `rag_initialize_requested` |
| Reload RAG | Search & knowledge | Explicitly saves valid RAG edits, then emits `rag_reload_requested` |
| Queue RAG reindex | Search & knowledge | Emits `rag_reindex_requested`; never runs on open/search |

## Related QSettings outside the Settings window

These controls belong to their workflows and are not copied into a second
editable Settings control. They remain searchable through contextual links when
the owner screen is available.

| Keys | Current owner | Reason kept there |
| --- | --- | --- |
| `rec_config/model`, `rec_config/mic`, `rec_config/language`, `rec_config/diarization`, `rec_config/capture_system_audio`, `rec_config/auto_summarize_after_transcription`, `whisper_language` | Welcome capture workflow | Per-capture defaults are presented and saved by the capture form |
| `rec_config/diarization`, `rec_config/language` | Recording session / audio editor | Session-specific recording and editor configuration |
| `transcription_chunking_enabled`, `transcription_chunk_threshold_seconds`, `transcription_chunk_size_seconds`, `transcription_chunk_overlap_seconds` | Worker configuration | No current Settings control; runtime normalization is owned by worker settings |
| `recording_guardian/activity_amplitude_threshold` | Recording guardian | Internal runtime threshold, not a user-editable Settings control |
| `last_transcription_backend`, `last_transcription_model`, `last_transcription_device`, `last_transcription_force_cpu`, `last_transcription_compute_type` | Worker diagnostics | Written as last-run facts, not user preferences |
| `task_list/*` | Tasks board | Owned by its feature panel and saved there |
| Recurring-meeting templates and occurrences | Meeting scheduler/database | Domain records, not QSettings preferences |
| `settings/category`, `settings/advanced_mode`, `settings/pending_restart*` | Settings navigation metadata | Local UI state and pending-application status; never sent to runtime consumers |

Pomodoro duration and notification preferences previously edited in the Pomodoro
view are now edited only in **Automation & notifications**; its view shows the
saved defaults and reads them when starting a new interval. Recurring meeting
templates remain in the meeting owner because they are persisted domain records,
not global preferences. The current Settings actions emit three real Qt signals for explicit RAG
operations. Other externally visible settings are consumed by the modules named
above; tests in `tests/ui/settings/` and `tests/integration/` establish the
round-trip and active-runtime contracts before controls are reshaped.
