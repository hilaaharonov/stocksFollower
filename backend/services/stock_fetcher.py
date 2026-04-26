"""Stock data fetching service using yfinance."""

import logging
from datetime import datetime, timezone
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)


def fetch_stock_info(symbol: str) -> dict:
    """Fetch basic stock info (name, sector, etc.)."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            "symbol": symbol.upper(),
            "name": info.get("longName") or info.get("shortName") or symbol.upper(),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("marketCap"),
            "currency": info.get("currency", "USD"),
        }
    except Exception as exc:
        logger.warning("Could not fetch info for %s: %s", symbol, exc)
        return {"symbol": symbol.upper(), "name": symbol.upper()}


def fetch_latest_price(symbol: str) -> Optional[dict]:
    """Fetch the latest OHLCV data point for a symbol."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d", interval="1m")
        if hist.empty:
            logger.warning("No price data returned for %s", symbol)
            return None
        last = hist.iloc[-1]
        return {
            "symbol": symbol.upper(),
            "timestamp": datetime.now(timezone.utc),
            "open": float(last["Open"]),
            "high": float(last["High"]),
            "low": float(last["Low"]),
            "close": float(last["Close"]),
            "volume": float(last["Volume"]),
        }
    except Exception as exc:
        logger.error("Error fetching latest price for %s: %s", symbol, exc)
        return None


def fetch_historical_data(symbol: str, period: str = "1mo", interval: str = "1d") -> list[dict]:
    """Fetch historical OHLCV data for a symbol.

    Args:
        symbol: Stock ticker symbol.
        period: yfinance period string (e.g. '1d', '5d', '1mo', '3mo', '1y').
        interval: yfinance interval string (e.g. '1m', '5m', '1h', '1d').

    Returns:
        List of OHLCV dicts with UTC timestamps.
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        if hist.empty:
            return []
        records = []
        for ts, row in hist.iterrows():
            # Convert pandas Timestamp to python datetime
            if hasattr(ts, "to_pydatetime"):
                dt = ts.to_pydatetime()
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = datetime.now(timezone.utc)
            records.append(
                {
                    "symbol": symbol.upper(),
                    "timestamp": dt,
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": float(row["Volume"]),
                }
            )
        return records
    except Exception as exc:
        logger.error("Error fetching historical data for %s: %s", symbol, exc)
        return []
