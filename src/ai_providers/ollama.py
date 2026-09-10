"""Ollama local-provider adapter and availability helpers."""

import logging
from typing import Dict, List

from src.ai_providers.interfaces import AIProvider

DEFAULT_OLLAMA_HOST = "http://localhost:11434"


class OllamaProvider(AIProvider):
    """Ollama local LLM provider."""

    def __init__(self, host: str = DEFAULT_OLLAMA_HOST, model_name: str = "llama3"):
        self.host = host
        self.model_name = model_name
        try:
            import ollama

            self.client = ollama.Client(host=host)
        except ImportError as error:
            raise ImportError("Ollama library not installed. Please run: pip install ollama") from error
        except Exception as error:
            raise ConnectionError(f"Failed to connect to Ollama at {host}: {error}") from error

    def generate_content(self, prompt: str) -> str:
        try:
            return self.client.generate(model=self.model_name, prompt=prompt).get("response", "")
        except Exception as error:
            logging.error("Ollama error: %s", error)
            raise RuntimeError(str(error)) from error

    def chat(self, history: List[Dict[str, str]], prompt: str, context: str = "") -> str:
        system_message = """You are a helpful assistant that answers questions based on the user's notes and transcriptions.
Use the provided context to answer the question. If the answer is not in the context, say you don't know based on the notes, but try to be as helpful as possible."""
        if context:
            system_message += f"\n\nContext:\n{context}"
        messages = [{"role": "system", "content": system_message}]
        messages.extend(
            {"role": "user" if message["role"] == "user" else "assistant", "content": message["content"]}
            for message in history
        )
        messages.append({"role": "user", "content": prompt})
        return self.client.chat(model=self.model_name, messages=messages)["message"]["content"]


def get_available_ollama_models(host: str = DEFAULT_OLLAMA_HOST) -> List[str]:
    """Return locally installed Ollama model names, or an empty list on failure."""
    try:
        import ollama

        response = ollama.Client(host=host).list()
        return [model.model for model in (response.models if hasattr(response, "models") else [])]
    except ImportError:
        logging.warning("Ollama library not installed")
    except Exception as error:
        logging.warning("Failed to list Ollama models: %s", error)
    return []


def is_ollama_available(host: str = DEFAULT_OLLAMA_HOST) -> bool:
    """Return whether the configured local Ollama server answers a health check."""
    try:
        import ollama

        ollama.Client(host=host).list()
        return True
    except Exception:
        return False
