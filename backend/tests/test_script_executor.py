"""Tests for the script executor service."""
import pytest
from services.script_executor import run_script, validate_script


def test_validate_valid_script():
    code = "x = 1 + 1"
    assert validate_script(code) is None


def test_validate_invalid_script():
    code = "def bad(:\n  pass"
    result = validate_script(code)
    assert result is not None
    assert "error" in result.lower() or "syntax" in result.lower()


def test_run_script_no_alerts():
    code = "x = context['close']"
    alerts = run_script(code, {"close": 100.0, "open": 99.0, "symbol": "AAPL"})
    assert alerts == []


def test_run_script_generates_alert():
    code = """
if context.get('close') and context.get('open'):
    change = (context['close'] - context['open']) / context['open'] * 100
    if change < -5:
        context['alerts'].append(f"Price dropped {change:.2f}%")
"""
    data = {"symbol": "AAPL", "open": 100.0, "close": 90.0}
    alerts = run_script(code, data)
    assert len(alerts) == 1
    assert "dropped" in alerts[0]


def test_run_script_no_alert_when_condition_not_met():
    code = """
if context.get('close') and context.get('open'):
    change = (context['close'] - context['open']) / context['open'] * 100
    if change < -5:
        context['alerts'].append("Price dropped significantly")
"""
    data = {"symbol": "AAPL", "open": 100.0, "close": 101.0}
    alerts = run_script(code, data)
    assert alerts == []


def test_run_script_handles_exception_gracefully():
    code = "raise ValueError('oops')"
    alerts = run_script(code, {"symbol": "AAPL"})
    assert len(alerts) == 1
    assert "Script execution failed" in alerts[0]


def test_run_script_restricted_builtins():
    """Scripts should not be able to import modules."""
    code = "__import__('os').system('echo hello')"
    alerts = run_script(code, {"symbol": "AAPL"})
    # Should raise NameError because __import__ is not in safe builtins
    assert any("Script execution failed" in a for a in alerts)
