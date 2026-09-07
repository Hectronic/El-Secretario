"""Platform-specific runtime policy for the RAG engine."""

from dataclasses import dataclass
from typing import Mapping


def _enabled(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


@dataclass(frozen=True)
class RAGRuntimePolicy:
    """Select safe Chroma execution modes without coupling them to the facade."""

    is_windows: bool
    safe_delete_mode: bool
    subprocess_upsert_mode: bool
    subprocess_query_mode: bool

    @classmethod
    def resolve(cls, platform_name: str, environ: Mapping[str, str]) -> "RAGRuntimePolicy":
        is_windows = platform_name == "Windows"
        return cls(
            is_windows=is_windows,
            safe_delete_mode=is_windows and _enabled(environ.get("EL_SECRETARIO_CHROMA_SAFE_DELETE", "1")),
            subprocess_upsert_mode=is_windows and _enabled(
                environ.get("EL_SECRETARIO_RAG_SUBPROCESS_UPSERT", "1")
            ),
            subprocess_query_mode=is_windows and _enabled(
                environ.get("EL_SECRETARIO_RAG_SUBPROCESS_QUERY", "1")
            ),
        )
