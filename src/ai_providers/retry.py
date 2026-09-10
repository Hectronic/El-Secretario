"""Provider-agnostic generation retry policy."""

import logging
import re
import time
from typing import Callable, Optional

from src.ai_providers.factory import get_provider_type
from src.ai_providers.interfaces import AIProvider

NON_OLLAMA_MAX_RETRIES = 2
NON_OLLAMA_BASE_BACKOFF_SECONDS = 1.0
NON_OLLAMA_PRE_REQUEST_DELAY_SECONDS = 0.35
NON_OLLAMA_MAX_BACKOFF_SECONDS = 16.0
NON_RETRYABLE_RATE_LIMIT_PATTERNS = (
    "429", "quota", "rate limit", "rate_limit", "resource_exhausted", "resource exhausted",
)


def extract_retry_delay_seconds(error: Exception | str) -> float | None:
    """Extract a provider-suggested delay from known Gemini error formats."""
    text = str(error or "")
    direct = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", text, flags=re.IGNORECASE)
    structured = re.search(
        r"retry_delay\s*\{[^}]*seconds:\s*([0-9]+)", text, flags=re.IGNORECASE | re.DOTALL
    )
    match = direct or structured
    if not match:
        return None
    try:
        return max(0.0, float(match.group(1)))
    except (TypeError, ValueError):
        return None


def is_non_retryable_rate_limit_error(error: Exception | str) -> bool:
    """Identify exhausted-quota errors that must not consume another API attempt."""
    return any(pattern in str(error or "").lower() for pattern in NON_RETRYABLE_RATE_LIMIT_PATTERNS)


def generate_content_with_retry(
    provider: AIProvider,
    settings,
    prompt: str,
    operation_name: str = "AI generation",
    max_retries: int = NON_OLLAMA_MAX_RETRIES,
    base_backoff_seconds: float = NON_OLLAMA_BASE_BACKOFF_SECONDS,
    on_retry: Optional[Callable[[float, int, int, str], None]] = None,
    *,
    provider_type: Optional[str] = None,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    """Generate with bounded cloud retries and one local-Ollama attempt."""
    selected_type = provider_type or get_provider_type(settings)
    is_ollama = selected_type == "ollama"
    attempts = 1 if is_ollama else max(1, int(max_retries))
    if not is_ollama:
        sleep(NON_OLLAMA_PRE_REQUEST_DELAY_SECONDS)

    last_error = None
    attempts_made = 0
    for attempt in range(1, attempts + 1):
        attempts_made = attempt
        try:
            text = str(provider.generate_content(prompt) or "").strip()
            if text:
                return text
            last_error = RuntimeError("Empty response from AI provider.")
        except Exception as error:
            last_error = error

        if not is_ollama and is_non_retryable_rate_limit_error(last_error):
            logging.warning("%s failed with quota/rate-limit error. Not retrying. Error: %s", operation_name, last_error)
            break
        if attempt >= attempts:
            break
        delay = extract_retry_delay_seconds(last_error)
        if delay is None:
            delay = min(base_backoff_seconds * (2 ** (attempt - 1)), NON_OLLAMA_MAX_BACKOFF_SECONDS)
        logging.warning("%s failed (attempt %s/%s). Retrying in %.1fs. Error: %s", operation_name, attempt, attempts, delay, last_error)
        if on_retry:
            try:
                on_retry(delay, attempt, attempts, str(last_error))
            except Exception:
                pass
        sleep(delay)

    raise RuntimeError(f"{operation_name} failed after {attempts_made} attempts: {last_error}")
