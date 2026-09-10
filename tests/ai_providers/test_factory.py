from src.ai_providers.factory import get_ai_provider, validate_ai_provider_config


class _Settings:
    def __init__(self, values):
        self.values = values

    def value(self, key, default=None):
        return self.values.get(key, default)


def test_factory_uses_configured_ollama_adapter_without_importing_network_client():
    created = []

    provider = get_ai_provider(
        _Settings({"ai_provider": "ollama", "ollama_host": "http://local", "ollama_model": "mistral"}),
        ollama_provider_cls=lambda **kwargs: created.append(kwargs) or "ollama-provider",
    )

    assert provider == "ollama-provider"
    assert created == [{"host": "http://local", "model_name": "mistral"}]


def test_validation_returns_user_facing_ollama_and_gemini_errors():
    unavailable = _Settings({"ai_provider": "ollama", "ollama_model": "mistral"})
    assert validate_ai_provider_config(unavailable, ollama_available=lambda _host: False)[0] is False

    missing_key = _Settings({"ai_provider": "gemini", "gemini_key": ""})
    assert validate_ai_provider_config(missing_key) == (
        False,
        "Gemini API Key missing. Go to Settings to add it.",
    )
