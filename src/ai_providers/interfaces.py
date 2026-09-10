"""Provider protocol shared by cloud and local AI adapters."""

from abc import ABC, abstractmethod
from typing import Dict, List


class AIProvider(ABC):
    """Abstract interface for generation and contextual chat providers."""

    @abstractmethod
    def generate_content(self, prompt: str) -> str:
        """Generate content for one prompt."""

    @abstractmethod
    def chat(self, history: List[Dict[str, str]], prompt: str, context: str = "") -> str:
        """Answer a chat prompt using optional history and context."""
