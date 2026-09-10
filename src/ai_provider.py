# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Backward-compatible public imports for AI provider functionality."""

from src.ai_providers import (
    AIProvider,
    DEFAULT_OLLAMA_HOST,
    GEMINI_MODELS,
    GeminiProvider,
    OllamaProvider,
    generate_content_with_retry,
    get_ai_provider,
    get_available_ollama_models,
    get_provider_type as _get_provider_type,
    is_ollama_available,
    validate_ai_provider_config,
)
from src.ai_providers.retry import (
    extract_retry_delay_seconds as _extract_retry_delay_seconds,
)
from src.ai_providers.retry import (
    is_non_retryable_rate_limit_error as _is_non_retryable_rate_limit_error,
)

__all__ = [
    "AIProvider", "DEFAULT_OLLAMA_HOST", "GEMINI_MODELS", "GeminiProvider",
    "OllamaProvider", "generate_content_with_retry", "get_ai_provider",
    "get_available_ollama_models", "is_ollama_available",
    "validate_ai_provider_config",
]
