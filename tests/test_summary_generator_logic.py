# Copyright (C) 2026 Héctor Álvarez López <hectoralvarez.me>
import pytest
from unittest.mock import MagicMock, patch
from src.summary_generator import SummaryGenerator

@pytest.fixture
def mock_db():
    with patch('src.summary_generator.DBManager') as mock:
        instance = mock.return_value
        instance.get_dates_with_content.return_value = ["2026-04-10"]
        instance.get_weeks_without_summary.return_value = ["2026-04-12"]
        # Use dicts because the code uses .get()
        instance.get_recordings_without_summary.return_value = [
            {'id': 1, 'title': 'Rec 1', 'transcription': 'Test', 'summary': '', 'recording_notes': ''}
        ]
        instance.fetch_by_dates.return_value = [
            {'id': 1, 'title': 'Rec 1', 'transcription': 'Test', 'summary': '', 'recording_notes': ''}
        ]
        instance.get_daily_summary.return_value = None
        instance.compose_ai_text.return_value = "Composed Text"
        yield instance

@pytest.fixture
def mock_ai_retry():
    with patch('src.summary_generator.generate_content_with_retry') as mock:
        mock.return_value = "Mocked AI Summary"
        yield mock

@pytest.fixture
def mock_ai_provider():
    with patch('src.summary_generator.get_ai_provider') as mock_get:
        mock_provider = MagicMock()
        mock_get.return_value = mock_provider
        
        with patch('src.summary_generator.validate_ai_provider_config') as mock_val:
            mock_val.return_value = (True, "")
            yield mock_provider

@pytest.fixture
def mock_settings():
    with patch('src.summary_generator.QSettings') as mock:
        instance = mock.return_value
        # Important: system_language, ai_provider, prompt_...
        instance.value.side_effect = lambda key, default=None: default
        yield instance

def test_summary_generator_validation_fails(qtbot, mock_db, mock_settings):
    with patch('src.summary_generator.validate_ai_provider_config') as mock_val:
        mock_val.return_value = (False, "Invalid Config")
        gen = SummaryGenerator(generate_daily=True)
        with qtbot.waitSignal(gen.error, timeout=2000) as blocker:
            gen.start()
        assert blocker.args[0] == "Invalid Config"

def test_summary_generator_daily_flow(qtbot, mock_db, mock_ai_provider, mock_ai_retry, mock_settings):
    # Ensure generate_recordings=True so it processes them and sets processed_rec_for_day
    gen = SummaryGenerator(generate_daily=True, generate_weekly=False, generate_recordings=True, exclude_today=False)
    
    completed_items = []
    gen.item_completed.connect(lambda t, d, s: completed_items.append((t, d)))
    
    with qtbot.waitSignal(gen.all_tasks_finished, timeout=5000):
        gen.start()
        
    # Should have 'recording' and 'daily'
    types = [item[0] for item in completed_items]
    assert "recording" in types
    assert "daily" in types
    assert mock_ai_retry.called

def test_summary_generator_cancellation(qtbot, mock_db, mock_ai_provider, mock_settings):
    gen = SummaryGenerator()
    gen.cancel()
    with qtbot.waitSignal(gen.all_tasks_finished, timeout=2000) as blocker:
        gen.start()
    assert blocker.args == [0, 0, 0]

def test_summary_generator_specific_dates(qtbot, mock_db, mock_ai_provider, mock_ai_retry, mock_settings):
    gen = SummaryGenerator(
        specific_dates=["2026-05-01"],
        generate_weekly=False,
        generate_recordings=True,
        exclude_today=False,
    )
    
    completed_dates = []
    gen.item_completed.connect(lambda t, d, s: completed_dates.append(d))
    
    with qtbot.waitSignal(gen.all_tasks_finished, timeout=2000):
        gen.start()
        
    assert "2026-05-01" in completed_dates
    assert not mock_db.get_dates_with_content.called

def test_summary_generator_weekly_flow(qtbot, mock_db, mock_ai_provider, mock_ai_retry, mock_settings):
    mock_db.get_dates_with_content.return_value = []
    mock_db.get_weeks_without_summary.return_value = ["2026-04-12"]
    
    gen = SummaryGenerator(generate_daily=False, generate_weekly=True, generate_recordings=False)
    
    completed_items = []
    gen.item_completed.connect(lambda t, d, s: completed_items.append((t, d)))
    
    with qtbot.waitSignal(gen.all_tasks_finished, timeout=5000):
        gen.start()
        
    assert ("weekly", "2026-04-12") in completed_items
    assert mock_ai_retry.called
