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
from typing import List, Dict, Optional
import logging

# Available Gemini models
GEMINI_MODELS = [
    "gemini-3-flash-preview",
    "gemini-3-preview",
]

DEFAULT_OLLAMA_HOST = "http://localhost:11434"


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
        
        import google.generativeai as genai
        self.genai = genai
        self.api_key = api_key
        self.model_name = model_name
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
    
    def generate_content(self, prompt: str) -> str:
        response = self.model.generate_content(prompt)
        return response.text
    
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
        
        response = self.model.generate_content(full_prompt)
        return response.text


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
        response = self.client.generate(model=self.model_name, prompt=prompt)
        return response['response']
    
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
