"""Stocks router: manage watched stocks and retrieve price data."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import WatchedStock, get_db
from services.influxdb_writer import query_latest_prices, write_price_batch
from services.stock_fetcher import fetch_stock_info, fetch_historical_data

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stocks", tags=["stocks"])


class StockAdd(BaseModel):
    symbol: str
    name: Optional[str] = None


class StockOut(BaseModel):
    id: int
    symbol: str
    name: Optional[str]
    active: bool

    class Config:
        from_attributes = True


@router.get("", response_model=list[StockOut])
def list_stocks(db: Session = Depends(get_db)):
    """List all watched stocks."""
    return db.query(WatchedStock).all()


@router.post("", response_model=StockOut, status_code=201)
def add_stock(payload: StockAdd, db: Session = Depends(get_db)):
    """Add a stock to the watch list."""
    symbol = payload.symbol.upper().strip()
    existing = db.query(WatchedStock).filter(WatchedStock.symbol == symbol).first()
    if existing:
        if not existing.active:
            existing.active = True
            db.commit()
            db.refresh(existing)
            return existing
        raise HTTPException(status_code=409, detail=f"{symbol} is already being watched")

    # Fetch info from yfinance to get the company name
    name = payload.name
    if not name:
        info = fetch_stock_info(symbol)
        name = info.get("name", symbol)

    stock = WatchedStock(symbol=symbol, name=name)
    db.add(stock)
    db.commit()
    db.refresh(stock)
    return stock


@router.delete("/{symbol}", status_code=204)
def remove_stock(symbol: str, db: Session = Depends(get_db)):
    """Remove (deactivate) a stock from the watch list."""
    symbol = symbol.upper()
    stock = db.query(WatchedStock).filter(WatchedStock.symbol == symbol).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"{symbol} not found")
    stock.active = False
    db.commit()


@router.get("/{symbol}/data")
def get_stock_data(
    symbol: str,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get recent price data for a stock from InfluxDB."""
    symbol = symbol.upper()
    stock = db.query(WatchedStock).filter(WatchedStock.symbol == symbol, WatchedStock.active == True).first()  # noqa: E712
    if not stock:
        raise HTTPException(status_code=404, detail=f"{symbol} not found in watch list")
    prices = query_latest_prices(symbol, limit=limit)
    return {"symbol": symbol, "count": len(prices), "data": prices}


@router.post("/{symbol}/fetch", status_code=202)
def trigger_fetch(
    symbol: str,
    period: str = Query(default="1mo", description="yfinance period, e.g. 1d, 5d, 1mo, 3mo, 1y"),
    interval: str = Query(default="1d", description="yfinance interval, e.g. 1m, 5m, 1h, 1d"),
    db: Session = Depends(get_db),
):
    """Manually trigger a historical data fetch for a stock."""
    symbol = symbol.upper()
    stock = db.query(WatchedStock).filter(WatchedStock.symbol == symbol).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"{symbol} not found in watch list")

    records = fetch_historical_data(symbol, period=period, interval=interval)
    if not records:
        raise HTTPException(status_code=502, detail=f"No data returned for {symbol}")

    write_price_batch(records)
    return {"symbol": symbol, "fetched": len(records), "period": period, "interval": interval}
