"""Stock data fetching service using yfinance."""

import logging
from datetime import datetime, timezone
from typing import Optional

import yfinance as yf

logger = logging.getLogger(__name__)


def get_stock_quote(symbol: str) -> Optional[dict]:
    """Fetch the current live quote for a stock symbol.

    Returns a flat dict with price, OHLC, volume, name, and currency,
    or None if the data cannot be retrieved.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period="1d", interval="1m")

        price: Optional[float] = None
        if not hist.empty:
            price = float(hist.iloc[-1]["Close"])
        elif info.get("regularMarketPrice"):
            price = float(info["regularMarketPrice"])

        if price is None:
            logger.warning("No price data available for %s", symbol)
            return None

        return {
            "symbol": symbol.upper(),
            "name": info.get("longName") or info.get("shortName") or symbol.upper(),
            "price": price,
            "open": float(hist.iloc[0]["Open"]) if not hist.empty else None,
            "high": float(hist["High"].max()) if not hist.empty else None,
            "low": float(hist["Low"].min()) if not hist.empty else None,
            "volume": float(hist["Volume"].sum()) if not hist.empty else None,
            "currency": info.get("currency", "USD"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("Error fetching quote for %s: %s", symbol, exc)
        return None


def get_stock_history(symbol: str, period: str = "1mo", interval: str = "1d") -> list[dict]:
    """Fetch historical OHLCV data for a stock symbol.

    Args:
        symbol:   Ticker symbol (e.g. "AAPL").
        period:   yfinance period string – e.g. "1d", "5d", "1mo", "3mo", "1y".
        interval: yfinance interval string – e.g. "1m", "5m", "1h", "1d", "1wk".

    Returns:
        List of OHLCV dicts sorted oldest-first, each containing an ISO-8601
        "time" string plus open, high, low, close, and volume fields.
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)
        if hist.empty:
            logger.warning("No historical data returned for %s", symbol)
            return []

        records: list[dict] = []
        for ts, row in hist.iterrows():
            dt = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else datetime.now(timezone.utc)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            records.append(
                {
                    "time": dt.isoformat(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": float(row["Volume"]),
                }
            )
        return records
    except Exception as exc:
        logger.error("Error fetching history for %s: %s", symbol, exc)
        return []
