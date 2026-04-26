"""Integration tests for the FastAPI endpoints.

These tests use a TestClient with an in-memory SQLite database and mock out
external calls (InfluxDB, yfinance) to keep tests fast and hermetic.
"""
import os
import pytest
from unittest.mock import patch, MagicMock

# Set env before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///./test_app.db"
os.environ["INFLUXDB_URL"] = "http://localhost:8086"
os.environ["INFLUXDB_TOKEN"] = "test-token"
os.environ["INFLUXDB_ORG"] = "stocks"
os.environ["INFLUXDB_BUCKET"] = "stocks"

from fastapi.testclient import TestClient
import database
from database import Base, engine


@pytest.fixture(autouse=True)
def reset_db():
    """Re-create tables before each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    # Patch scheduler so it doesn't actually start
    with patch("scheduler.start_scheduler"), patch("scheduler.stop_scheduler"):
        from main import app
        with TestClient(app) as c:
            yield c


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Stocks
# ---------------------------------------------------------------------------

@patch("routers.stocks.fetch_stock_info", return_value={"name": "Apple Inc.", "symbol": "AAPL"})
def test_add_and_list_stock(mock_info, client):
    resp = client.post("/api/stocks", json={"symbol": "aapl"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert data["name"] == "Apple Inc."

    resp = client.get("/api/stocks")
    assert resp.status_code == 200
    symbols = [s["symbol"] for s in resp.json()]
    assert "AAPL" in symbols


@patch("routers.stocks.fetch_stock_info", return_value={"name": "Apple Inc.", "symbol": "AAPL"})
def test_add_duplicate_stock(mock_info, client):
    client.post("/api/stocks", json={"symbol": "AAPL"})
    resp = client.post("/api/stocks", json={"symbol": "AAPL"})
    assert resp.status_code == 409


@patch("routers.stocks.fetch_stock_info", return_value={"name": "Apple Inc.", "symbol": "AAPL"})
def test_remove_stock(mock_info, client):
    client.post("/api/stocks", json={"symbol": "AAPL"})
    resp = client.delete("/api/stocks/AAPL")
    assert resp.status_code == 204


def test_remove_nonexistent_stock(client):
    resp = client.delete("/api/stocks/FAKE")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Scripts
# ---------------------------------------------------------------------------

def test_create_script(client):
    payload = {
        "name": "Drop Alert",
        "code": "context['alerts'].append('test')",
        "enabled": True,
    }
    resp = client.post("/api/scripts", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Drop Alert"
    assert data["id"] > 0


def test_create_invalid_script(client):
    payload = {"name": "Bad", "code": "def bad(:\n  pass"}
    resp = client.post("/api/scripts", json=payload)
    assert resp.status_code == 422


def test_list_scripts(client):
    client.post("/api/scripts", json={"name": "S1", "code": "pass"})
    client.post("/api/scripts", json={"name": "S2", "code": "pass"})
    resp = client.get("/api/scripts")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_update_script(client):
    resp = client.post("/api/scripts", json={"name": "Old", "code": "pass"})
    sid = resp.json()["id"]
    resp = client.put(f"/api/scripts/{sid}", json={"name": "New"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"


def test_delete_script(client):
    resp = client.post("/api/scripts", json={"name": "ToDelete", "code": "pass"})
    sid = resp.json()["id"]
    resp = client.delete(f"/api/scripts/{sid}")
    assert resp.status_code == 204
    resp = client.get("/api/scripts")
    assert all(s["id"] != sid for s in resp.json())


@patch("routers.scripts.fetch_latest_price")
def test_run_script_with_symbol(mock_price, client):
    mock_price.return_value = {
        "symbol": "AAPL",
        "open": 100.0,
        "close": 90.0,
        "high": 101.0,
        "low": 89.0,
        "volume": 1000.0,
    }
    resp = client.post("/api/scripts", json={
        "name": "TestRun",
        "code": "context['alerts'].append('triggered')",
        "symbol": "AAPL",
    })
    sid = resp.json()["id"]
    resp = client.post(f"/api/scripts/{sid}/run", params={"symbol": "AAPL"})
    assert resp.status_code == 200
    assert "triggered" in resp.json()["alerts"]


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

def test_list_alerts_empty(client):
    resp = client.get("/api/alerts")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# AI Notes
# ---------------------------------------------------------------------------

def test_get_ai_note_not_found(client):
    resp = client.get("/api/ai/notes/AAPL")
    assert resp.status_code == 404


@patch("routers.stocks.fetch_stock_info", return_value={"name": "Apple Inc.", "symbol": "AAPL"})
@patch("routers.ai_notes.fetch_stock_info", return_value={"name": "Apple Inc.", "sector": "Technology"})
@patch("routers.ai_notes.query_latest_prices", return_value=[])
@patch("routers.ai_notes.generate_ai_note", return_value="Apple is a tech giant.")
def test_refresh_and_get_ai_note(mock_gen, mock_prices, mock_info_ai, mock_info_stock, client):
    # Add stock first
    client.post("/api/stocks", json={"symbol": "AAPL"})
    # Generate note
    resp = client.post("/api/ai/notes/AAPL/refresh")
    assert resp.status_code == 201
    assert resp.json()["note"] == "Apple is a tech giant."
    # Retrieve note
    resp = client.get("/api/ai/notes/AAPL")
    assert resp.status_code == 200
    assert resp.json()["note"] == "Apple is a tech giant."


@patch("routers.ai_notes.fetch_stock_info", return_value={})
@patch("routers.ai_notes.query_latest_prices", return_value=[])
@patch("routers.ai_notes.generate_ai_note", return_value="Some note.")
def test_refresh_ai_note_unwatched_symbol(mock_gen, mock_prices, mock_info, client):
    resp = client.post("/api/ai/notes/FAKE/refresh")
    assert resp.status_code == 404
