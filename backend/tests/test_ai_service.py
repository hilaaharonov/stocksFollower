"""Tests for the AI notes service."""
import pytest
from unittest.mock import patch

from services.ai_service import _generate_basic_note, generate_ai_note


def test_basic_note_no_data():
    note = _generate_basic_note("AAPL", {}, [])
    assert "AAPL" in note
    assert "informational" in note.lower() or "advice" in note.lower()


def test_basic_note_with_sector():
    note = _generate_basic_note("AAPL", {"name": "Apple Inc.", "sector": "Technology"}, [])
    assert "Technology" in note
    assert "Apple" in note


def test_basic_note_with_price_data():
    prices = [
        {"close": 150.0},
        {"close": 148.0},
        {"close": 145.0},
        {"close": 143.0},
        {"close": 140.0},
    ]
    note = _generate_basic_note("AAPL", {"name": "Apple Inc."}, prices)
    assert "150" in note
    assert "upward" in note or "downward" in note or "flat" in note


def test_basic_note_downward_trend():
    prices = [
        {"close": 100.0},
        {"close": 105.0},
        {"close": 110.0},
        {"close": 115.0},
        {"close": 120.0},
    ]
    note = _generate_basic_note("AAPL", {"name": "Apple Inc."}, prices)
    assert "downward" in note


def test_generate_ai_note_no_api_key():
    """When OpenAI API key is not set, should fall back to basic note."""
    with patch("services.ai_service.settings") as mock_settings:
        mock_settings.openai_api_key = ""
        note = generate_ai_note("TSLA", {"name": "Tesla Inc."}, [])
    assert "TSLA" in note
