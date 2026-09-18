"""Pure drag-and-drop validation helpers for audio imports."""

from pathlib import Path

SUPPORTED_AUDIO_EXTENSIONS = frozenset({".mp3", ".wav", ".m4a", ".flac", ".ogg"})


def is_supported_audio_path(path: str) -> bool:
    """Return whether *path* is a local regular file in a supported format."""
    candidate = Path(path)
    return candidate.is_file() and candidate.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS


def extract_supported_audio_path(mime_data) -> str | None:
    """Extract one supported local audio file from Qt mime data."""
    if not mime_data.hasUrls():
        return None
    urls = mime_data.urls()
    if len(urls) != 1:
        return None
    url = urls[0]
    if not url.isLocalFile():
        return None
    path = url.toLocalFile()
    return path if is_supported_audio_path(path) else None
