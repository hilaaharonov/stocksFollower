"""Stocks router: list watched stocks and serve real-time price data."""

import logging

from fastapi import APIRouter, HTTPException, Query

from config import settings
from services.stock_fetcher import get_stock_quote, get_stock_history

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stocks", tags=["stocks"])

# Parse the watched symbols once at module load time.
# Add more symbols by setting WATCHED_STOCKS in your .env file.
_WATCHED_SYMBOLS: list[str] = [
    s.strip().upper() for s in settings.watched_stocks.split(",") if s.strip()
]


@router.get("")
def list_stocks() -> list[dict]:
    """Return the list of watched stock symbols (from config)."""
    return [{"symbol": s} for s in _WATCHED_SYMBOLS]


@router.get("/{symbol}/quote")
def get_quote(symbol: str) -> dict:
    """Fetch the current live quote for a stock symbol.

    Returns price, OHLC, volume, currency, and a UTC timestamp.
    The data is fetched from yfinance on every request – nothing is persisted.
    """
    symbol = symbol.upper()
    data = get_stock_quote(symbol)
    if data is None:
        raise HTTPException(status_code=502, detail=f"Could not fetch live data for {symbol}")
    return data


@router.get("/{symbol}/history")
def get_history(
    symbol: str,
    period: str = Query(
        default="1mo",
        description="yfinance period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y",
    ),
    interval: str = Query(
        default="1d",
        description="yfinance interval: 1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo",
    ),
) -> list[dict]:
    """Fetch historical OHLCV data for a stock symbol.

    Returns a list of OHLCV records sorted oldest-first.
    Each record contains an ISO-8601 ``time`` field plus open, high, low,
    close, and volume fields.
    Data is fetched from yfinance on every request – nothing is persisted.
    """
    symbol = symbol.upper()
    records = get_stock_history(symbol, period=period, interval=interval)
    if not records:
        raise HTTPException(
            status_code=502, detail=f"No historical data available for {symbol}"
        )
    return records
