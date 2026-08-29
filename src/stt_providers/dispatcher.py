# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import gc

from src.stt_providers import faster_whisper, openai_whisper, sherpa_onnx


BACKEND_HANDLERS = {
    "faster-whisper": faster_whisper.transcribe,
    "openai-whisper": openai_whisper.transcribe,
    "sherpa-onnx": sherpa_onnx.transcribe,
}


def subprocess_transcribe_entry(payload: dict, result_queue):
    """
    Run transcription in an isolated process.
    This keeps large native backends from retaining memory in the parent process.
    """
    backend = payload.get("backend", "faster-whisper")

    try:
        handler = BACKEND_HANDLERS.get(backend)
        if handler is None:
            raise RuntimeError(f"Unsupported transcription backend: {backend}")

        segments = handler(payload)
        result_queue.put({"ok": True, "segments": segments})
    except Exception as e:
        result_queue.put({"ok": False, "error": str(e)})
    finally:
        gc.collect()
