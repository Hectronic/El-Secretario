"""Google Gemini adapter."""

import logging
from typing import Dict, List

from src.ai_providers.interfaces import AIProvider


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
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            return response.text if response and hasattr(response, "text") else ""
        except Exception as error:
            logging.error("Gemini error: %s", error)
            raise RuntimeError(str(error)) from error

    def chat(self, history: List[Dict[str, str]], prompt: str, context: str = "") -> str:
        history_text = "".join(
            f"{'User' if message['role'] == 'user' else 'Assistant'}: {message['content']}\n"
            for message in history
        )
        full_prompt = f"""
        You are a helpful assistant that answers questions based on the user's notes and transcriptions.
        Use the provided context to answer the question. If the answer is not in the context, say you don't know based on the notes, but try to be as helpful as possible.

        Context:
        {context}

        Chat History:
        {history_text}

        User Question: {prompt}

        Assistant:
        """
        response = self.client.models.generate_content(model=self.model_name, contents=full_prompt)
        return response.text if response and hasattr(response, "text") else ""
