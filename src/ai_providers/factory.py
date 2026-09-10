"""Settings-driven provider construction and validation."""

from typing import Callable

from src.ai_providers.gemini import GeminiProvider
from src.ai_providers.interfaces import AIProvider
from src.ai_providers.ollama import DEFAULT_OLLAMA_HOST, OllamaProvider, is_ollama_available

GEMINI_MODELS = ["gemini-3-flash-preview", "gemini-3-preview"]


def get_provider_type(settings) -> str:
    """Normalize the configured provider name while preserving Gemini as default."""
    return str(settings.value("ai_provider", "gemini") or "gemini").strip().lower()


def get_ai_provider(
    settings,
    *,
    gemini_provider_cls: type[AIProvider] = GeminiProvider,
    ollama_provider_cls: type[AIProvider] = OllamaProvider,
) -> AIProvider:
    """Build the configured provider from settings."""
    if get_provider_type(settings) == "ollama":
        return ollama_provider_cls(
            host=settings.value("ollama_host", DEFAULT_OLLAMA_HOST),
            model_name=settings.value("ollama_model", "llama3"),
        )
    return gemini_provider_cls(
        api_key=settings.value("gemini_key", ""),
        model_name=settings.value("gemini_model", "gemini-3-flash-preview"),
    )


def validate_ai_provider_config(
    settings,
    *,
    ollama_available: Callable[[str], bool] = is_ollama_available,
) -> tuple[bool, str]:
    """Return a user-facing validation result for the configured provider."""
    if get_provider_type(settings) == "ollama":
        host = settings.value("ollama_host", DEFAULT_OLLAMA_HOST)
        if not settings.value("ollama_model", ""):
            return False, "No Ollama model selected. Go to Settings and select a model."
        if not ollama_available(host):
            return False, f"Ollama server not available at {host}. Make sure Ollama is running."
        return True, ""
    if not settings.value("gemini_key", ""):
        return False, "Gemini API Key missing. Go to Settings to add it."
    return True, ""
