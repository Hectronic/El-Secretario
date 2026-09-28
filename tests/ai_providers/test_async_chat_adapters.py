import asyncio
from types import SimpleNamespace

from src.ai_providers.gemini import GeminiProvider
from src.ai_providers.ollama import OllamaProvider


class _Response:
    text = "same answer"


def test_gemini_async_path_uses_same_prompt_as_sync_path():
    prompts = []

    class SyncModels:
        def generate_content(self, *, model, contents):
            prompts.append(contents)
            return _Response()

    class AsyncModels:
        async def generate_content(self, *, model, contents):
            prompts.append(contents)
            return _Response()

    provider = GeminiProvider.__new__(GeminiProvider)
    provider.model_name = "test-model"
    closed = []

    async def close_async_client():
        closed.append(True)

    provider.client = SimpleNamespace(
        models=SyncModels(), aio=SimpleNamespace(models=AsyncModels(), aclose=close_async_client)
    )
    history = [{"role": "user", "content": "Earlier"}]

    assert provider.chat(history, "Question", "Selected context") == "same answer"
    assert asyncio.run(provider.chat_async(history, "Question", "Selected context")) == "same answer"
    assert prompts[0] == prompts[1]
    assert closed == [True]


def test_ollama_async_path_uses_same_messages_and_closes_client(monkeypatch):
    messages_seen = []
    closed = []

    class SyncClient:
        def chat(self, *, model, messages):
            messages_seen.append(messages)
            return {"message": {"content": "same answer"}}

    class AsyncClient:
        def __init__(self, *, host):
            self._client = SimpleNamespace(aclose=self._close)

        async def _close(self):
            closed.append(True)

        async def chat(self, *, model, messages):
            messages_seen.append(messages)
            return {"message": {"content": "same answer"}}

    monkeypatch.setattr("ollama.AsyncClient", AsyncClient)
    provider = OllamaProvider.__new__(OllamaProvider)
    provider.host = "http://local"
    provider.model_name = "test-model"
    provider.client = SyncClient()
    history = [{"role": "user", "content": "Earlier"}]

    assert provider.chat(history, "Question", "Selected context") == "same answer"
    assert asyncio.run(provider.chat_async(history, "Question", "Selected context")) == "same answer"
    assert messages_seen[0] == messages_seen[1]
    assert closed == [True]
