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

"""
AI Provider abstraction layer.

This module provides an abstraction for different AI providers (Gemini, Ollama, etc.)
allowing the application to switch between them via configuration.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Callable, Optional
import logging
import time
import re

# Available Gemini models
GEMINI_MODELS = [
    "gemini-3-flash-preview",
    "gemini-3-preview",
]

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
NON_OLLAMA_MAX_RETRIES = 2
NON_OLLAMA_BASE_BACKOFF_SECONDS = 1.0
NON_OLLAMA_PRE_REQUEST_DELAY_SECONDS = 0.35
NON_OLLAMA_MAX_BACKOFF_SECONDS = 16.0
NON_RETRYABLE_RATE_LIMIT_PATTERNS = (
    "429",
    "quota",
    "rate limit",
    "rate_limit",
    "resource_exhausted",
    "resource exhausted",
)


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    @abstractmethod
    def generate_content(self, prompt: str) -> str:
        """Generate content based on a prompt.
        
        Args:
            prompt: The input prompt for generation.
            
        Returns:
            The generated text response.
        """
        pass
    
    @abstractmethod
    def chat(self, history: List[Dict[str, str]], prompt: str, context: str = "") -> str:
        """Chat with the AI using conversation history.
        
        Args:
            history: List of previous messages with 'role' and 'content' keys.
            prompt: The current user message.
            context: Optional context to include in the system prompt.
            
        Returns:
            The AI's response text.
        """
        pass


class GeminiProvider(AIProvider):
    """Google Gemini API provider."""
    
    def __init__(self, api_key: str, model_name: str = "gemini-3-flash-preview"):
        if not api_key:
            raise ValueError("Gemini API Key is missing.")

        from google import genai

        self.api_key = api_key
        self.model_name = model_name
        self.client = genai.Client(api_key=api_key)
    
    def generate_content(self, prompt: str) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            return response.text if response and hasattr(response, "text") else ""
        except Exception as e:
            logging.error(f"Gemini error: {e}")
            raise RuntimeError(str(e))
    
    def chat(self, history: List[Dict[str, str]], prompt: str, context: str = "") -> str:
        # Construct prompt with context and history
        history_str = ""
        for msg in history:
            role = "User" if msg['role'] == 'user' else "Assistant"
            history_str += f"{role}: {msg['content']}\n"

        full_prompt = f"""
        You are a helpful assistant that answers questions based on the user's notes and transcriptions.
        Use the provided context to answer the question. If the answer is not in the context, say you don't know based on the notes, but try to be as helpful as possible.
        
        Context:
        {context}
        
        Chat History:
        {history_str}
        
        User Question: {prompt}
        
        Assistant:
        """

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=full_prompt,
        )
        return response.text if response and hasattr(response, "text") else ""


class OllamaProvider(AIProvider):
    """Ollama local LLM provider."""
    
    def __init__(self, host: str = DEFAULT_OLLAMA_HOST, model_name: str = "llama3"):
        self.host = host
        self.model_name = model_name
        
        try:
            import ollama
            self.client = ollama.Client(host=host)
        except ImportError:
            raise ImportError("Ollama library not installed. Please run: pip install ollama")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Ollama at {host}: {e}")
    
    def generate_content(self, prompt: str) -> str:
        try:
            response = self.client.generate(model=self.model_name, prompt=prompt)
            return response.get('response', '')
        except Exception as e:
            logging.error(f"Ollama error: {e}")
            raise RuntimeError(str(e))
    
    def chat(self, history: List[Dict[str, str]], prompt: str, context: str = "") -> str:
        # Build messages list for Ollama chat format
        messages = []
        
        # Add system message with context
        system_message = """You are a helpful assistant that answers questions based on the user's notes and transcriptions.
Use the provided context to answer the question. If the answer is not in the context, say you don't know based on the notes, but try to be as helpful as possible."""
        
        if context:
            system_message += f"\n\nContext:\n{context}"
        
        messages.append({"role": "system", "content": system_message})
        
        # Add conversation history
        for msg in history:
            role = "user" if msg['role'] == 'user' else "assistant"
            messages.append({"role": role, "content": msg['content']})
        
        # Add current user message
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat(model=self.model_name, messages=messages)
        return response['message']['content']


def get_available_ollama_models(host: str = DEFAULT_OLLAMA_HOST) -> List[str]:
    """Get list of available Ollama models.
    
    Args:
        host: The Ollama server URL.
        
    Returns:
        List of model names available on the Ollama server.
    """
    try:
        import ollama
        client = ollama.Client(host=host)
        response = client.list()
        # The SDK returns a ListResponse object with a 'models' attribute
        # Each model is a Model object with a 'model' attribute for the name
        models = response.models if hasattr(response, 'models') else []
        return [model.model for model in models]
    except ImportError:
        logging.warning("Ollama library not installed")
        return []
    except Exception as e:
        logging.warning(f"Failed to list Ollama models: {e}")
        return []


def is_ollama_available(host: str = DEFAULT_OLLAMA_HOST) -> bool:
    """Check if Ollama server is running and accessible.
    
    Args:
        host: The Ollama server URL.
        
    Returns:
        True if Ollama is accessible, False otherwise.
    """
    try:
        import ollama
        client = ollama.Client(host=host)
        client.list()  # Try to list models as a health check
        return True
    except:
        return False


def get_ai_provider(settings) -> AIProvider:
    """Factory function to get the appropriate AI provider based on settings.
    
    Args:
        settings: QSettings object with the application configuration.
        
    Returns:
        An AIProvider instance configured according to settings.
        
    Raises:
        ValueError: If the provider configuration is invalid.
    """
    provider_type = settings.value("ai_provider", "gemini")
    
    if provider_type == "ollama":
        host = settings.value("ollama_host", DEFAULT_OLLAMA_HOST)
        model = settings.value("ollama_model", "llama3")
        return OllamaProvider(host=host, model_name=model)
    else:  # Default to Gemini
        api_key = settings.value("gemini_key", "")
        model = settings.value("gemini_model", "gemini-3-flash-preview")
        return GeminiProvider(api_key=api_key, model_name=model)


def validate_ai_provider_config(settings) -> tuple[bool, str]:
    """Validate that the AI provider is properly configured.
    
    Args:
        settings: QSettings object with the application configuration.
        
    Returns:
        A tuple of (is_valid, error_message). If is_valid is True, error_message is empty.
    """
    provider_type = settings.value("ai_provider", "gemini")
    
    if provider_type == "ollama":
        host = settings.value("ollama_host", DEFAULT_OLLAMA_HOST)
        model = settings.value("ollama_model", "")
        
        if not model:
            return False, "No Ollama model selected. Go to Settings and select a model."
        
        if not is_ollama_available(host):
            return False, f"Ollama server not available at {host}. Make sure Ollama is running."
        
        return True, ""
    else:  # Gemini
        api_key = settings.value("gemini_key", "")
        if not api_key:
            return False, "Gemini API Key missing. Go to Settings to add it."
        return True, ""


def _get_provider_type(settings) -> str:
    value = settings.value("ai_provider", "gemini")
    return str(value or "gemini").strip().lower()


def _extract_retry_delay_seconds(error: Exception | str) -> float | None:
    """
    Try to extract a provider-suggested retry delay from an error message.
    Supports patterns such as "Please retry in 18.65s" and "retry_delay { seconds: 18 }".
    """
    text = str(error or "")
    if not text:
        return None

    direct_match = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", text, flags=re.IGNORECASE)
    if direct_match:
        try:
            return max(0.0, float(direct_match.group(1)))
        except Exception:
            return None

    seconds_match = re.search(r"retry_delay\s*\{[^}]*seconds:\s*([0-9]+)", text, flags=re.IGNORECASE | re.DOTALL)
    if seconds_match:
        try:
            return max(0.0, float(seconds_match.group(1)))
        except Exception:
            return None

    return None


def _is_non_retryable_rate_limit_error(error: Exception | str) -> bool:
    text = str(error or "").lower()
    return any(pattern in text for pattern in NON_RETRYABLE_RATE_LIMIT_PATTERNS)


def generate_content_with_retry(
    provider: AIProvider,
    settings,
    prompt: str,
    operation_name: str = "AI generation",
    max_retries: int = NON_OLLAMA_MAX_RETRIES,
    base_backoff_seconds: float = NON_OLLAMA_BASE_BACKOFF_SECONDS,
    on_retry: Optional[Callable[[float, int, int, str], None]] = None,
) -> str:
    """
    Generate content with resilience for non-local providers.

    For Ollama: single attempt (local, usually no rate limits).
    For non-Ollama providers: add a small pre-delay and retry with exponential backoff.
    """
    provider_type = _get_provider_type(settings)
    is_ollama = provider_type == "ollama"
    total_attempts = 1 if is_ollama else max(1, int(max_retries))

    if not is_ollama:
        time.sleep(NON_OLLAMA_PRE_REQUEST_DELAY_SECONDS)

    last_error = None
    attempts_made = 0

    for attempt in range(1, total_attempts + 1):
        attempts_made = attempt
        try:
            result = provider.generate_content(prompt)
            text = str(result or "").strip()
            if text:
                return text
            last_error = RuntimeError("Empty response from AI provider.")
        except Exception as exc:
            last_error = exc

        if not is_ollama and _is_non_retryable_rate_limit_error(last_error):
            logging.warning(
                "%s failed with quota/rate-limit error. Not retrying. Error: %s",
                operation_name,
                last_error,
            )
            break

        if attempt >= total_attempts:
            break

        api_suggested_delay = _extract_retry_delay_seconds(last_error)
        if api_suggested_delay is not None:
            delay = api_suggested_delay
        else:
            delay = min(base_backoff_seconds * (2 ** (attempt - 1)), NON_OLLAMA_MAX_BACKOFF_SECONDS)
        logging.warning(
            "%s failed (attempt %s/%s). Retrying in %.1fs. Error: %s",
            operation_name,
            attempt,
            total_attempts,
            delay,
            last_error,
        )
        if on_retry:
            try:
                on_retry(delay, attempt, total_attempts, str(last_error))
            except Exception:
                pass
        time.sleep(delay)

    raise RuntimeError(f"{operation_name} failed after {attempts_made} attempts: {last_error}")
