"""Provider selection and retry contract with deterministic external edges."""

from src.ai_provider import generate_content_with_retry, get_ai_provider, validate_ai_provider_config


class _Settings:
    def __init__(self, values):
        self.values = values

    def value(self, key, default=None):
        return self.values.get(key, default)


class _Provider:
    def __init__(self):
        self.prompts = []

    def generate_content(self, prompt):
        self.prompts.append(prompt)
        return "  deterministic response  "


def test_provider_factory_validation_and_retry_form_a_deterministic_contract():
    settings = _Settings({"ai_provider": "ollama", "ollama_host": "http://local", "ollama_model": "local-model"})
    provider = _Provider()

    selected = get_ai_provider(settings, ollama_provider_cls=lambda **kwargs: provider)
    valid, message = validate_ai_provider_config(settings, ollama_available=lambda host: host == "http://local")
    response = generate_content_with_retry(
        selected,
        settings,
        "Summarize this",
        sleep=lambda _delay: None,
    )

    assert valid is True and message == ""
    assert response == "deterministic response"
    assert provider.prompts == ["Summarize this"]
