"""Tests for the StocksFollower backend."""
import pytest
from fastapi.testclient import TestClient

# Use an in-memory SQLite database for tests
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_stocks.db")
os.environ.setdefault("INFLUXDB_URL", "http://localhost:8086")
os.environ.setdefault("INFLUXDB_TOKEN", "test-token")
os.environ.setdefault("INFLUXDB_ORG", "stocks")
os.environ.setdefault("INFLUXDB_BUCKET", "stocks")
