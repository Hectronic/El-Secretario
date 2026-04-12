# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
import pytest
from unittest.mock import MagicMock, patch
from src.ai_provider import (
    _extract_retry_delay_seconds, 
    generate_content_with_retry,
    AIProvider
)

def test_extract_retry_delay_seconds_regex():
    # Test text-based format
    msg1 = "Please retry in 18.65s"
    assert _extract_retry_delay_seconds(msg1) == 18.65
    
    # Test structured format
    msg2 = "error { retry_delay { seconds: 12 } }"
    assert _extract_retry_delay_seconds(msg2) == 12.0
    
    # Test case insensitive
    assert _extract_retry_delay_seconds("RETRY IN 5S") == 5.0

@patch('time.sleep', return_value=None)
@patch('src.ai_provider._get_provider_type')
def test_generate_content_with_retry_success_after_failure(mock_get_type, mock_sleep, mock_settings):
    mock_get_type.return_value = 'gemini'
    mock_provider = MagicMock(spec=AIProvider)
    mock_provider.generate_content.side_effect = [
        RuntimeError("Temporary error"),
        "Successful Response"
    ]
    
    result = generate_content_with_retry(
        provider=mock_provider,
        settings=mock_settings,
        prompt="Hello",
        max_retries=3,
        base_backoff_seconds=0.1
    )
    
    assert result == "Successful Response"
    assert mock_provider.generate_content.call_count == 2

@patch('time.sleep', return_value=None)
@patch('src.ai_provider._get_provider_type')
def test_generate_content_with_retry_all_fails(mock_get_type, mock_sleep, mock_settings):
    mock_get_type.return_value = 'gemini'
    mock_provider = MagicMock(spec=AIProvider)
    mock_provider.generate_content.side_effect = RuntimeError("Persistent Error")
    
    with pytest.raises(RuntimeError, match="failed after 3 attempts"):
        generate_content_with_retry(
            provider=mock_provider,
            settings=mock_settings,
            prompt="Hello",
            max_retries=3,
            base_backoff_seconds=0.1
        )
    
    assert mock_provider.generate_content.call_count == 3

@patch('time.sleep', return_value=None)
@patch('src.ai_provider._get_provider_type')
def test_generate_content_with_retry_ollama_no_retry(mock_get_type, mock_sleep, mock_settings):
    mock_get_type.return_value = 'ollama'
    mock_provider = MagicMock(spec=AIProvider)
    mock_provider.generate_content.side_effect = RuntimeError("Ollama local error")
    
    with pytest.raises(RuntimeError, match="failed after 1 attempts"):
        generate_content_with_retry(
            provider=mock_provider,
            settings=mock_settings,
            prompt="Hello",
            max_retries=5
        )
    
    assert mock_provider.generate_content.call_count == 1

@pytest.fixture
def mock_settings():
    # Patch QSettings where it is used (inside src.ai_provider if it were there, 
    # but here we just need a mock object that has a .value() method)
    mock = MagicMock()
    mock.value.side_effect = lambda key, default=None: default
    return mock
