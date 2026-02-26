import unittest
from unittest.mock import patch

from src.ai_provider import AIProvider, generate_content_with_retry


class DummySettings:
    def __init__(self, provider_type):
        self._provider_type = provider_type

    def value(self, key, default=None):
        if key == "ai_provider":
            return self._provider_type
        return default


class FlakyProvider(AIProvider):
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def generate_content(self, prompt: str) -> str:
        self.calls += 1
        nxt = self.responses.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt

    def chat(self, history, prompt: str, context: str = "") -> str:
        return ""


class TestAIProviderRetry(unittest.TestCase):
    def test_non_ollama_retries_with_backoff_until_success(self):
        provider = FlakyProvider([
            RuntimeError("quota"),
            "",
            "ok response",
        ])
        settings = DummySettings("gemini")

        with patch("src.ai_provider.time.sleep") as mock_sleep:
            result = generate_content_with_retry(
                provider=provider,
                settings=settings,
                prompt="test",
                operation_name="unit-test",
            )

        self.assertEqual(result, "ok response")
        self.assertEqual(provider.calls, 3)
        self.assertEqual(mock_sleep.call_count, 3)
        self.assertEqual(mock_sleep.call_args_list[0].args[0], 0.35)
        self.assertEqual(mock_sleep.call_args_list[1].args[0], 1.0)
        self.assertEqual(mock_sleep.call_args_list[2].args[0], 2.0)

    def test_ollama_single_attempt_without_delay(self):
        provider = FlakyProvider([""])
        settings = DummySettings("ollama")

        with patch("src.ai_provider.time.sleep") as mock_sleep:
            with self.assertRaises(RuntimeError):
                generate_content_with_retry(
                    provider=provider,
                    settings=settings,
                    prompt="test",
                    operation_name="unit-test",
                )

        self.assertEqual(provider.calls, 1)
        mock_sleep.assert_not_called()

    def test_non_ollama_uses_api_retry_delay_when_present(self):
        provider = FlakyProvider([
            RuntimeError("429 quota exceeded. Please retry in 18.65601274s."),
            "ok",
        ])
        settings = DummySettings("gemini")

        with patch("src.ai_provider.time.sleep") as mock_sleep:
            result = generate_content_with_retry(
                provider=provider,
                settings=settings,
                prompt="test",
                operation_name="unit-test",
            )

        self.assertEqual(result, "ok")
        self.assertEqual(provider.calls, 2)
        # first sleep = pre-delay, second sleep = API suggested retry delay
        self.assertEqual(mock_sleep.call_count, 2)
        self.assertEqual(mock_sleep.call_args_list[0].args[0], 0.35)
        self.assertAlmostEqual(mock_sleep.call_args_list[1].args[0], 18.65601274, places=6)


if __name__ == "__main__":
    unittest.main()
