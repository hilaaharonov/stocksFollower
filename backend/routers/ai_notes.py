"""AI notes router."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import AiNote, WatchedStock, get_db
from services.ai_service import generate_ai_note
from services.influxdb_writer import query_latest_prices
from services.stock_fetcher import fetch_stock_info

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai", tags=["ai"])


class AiNoteOut(BaseModel):
    symbol: str
    note: str
    generated_at: datetime

    class Config:
        from_attributes = True


@router.get("/notes/{symbol}", response_model=AiNoteOut)
def get_ai_note(symbol: str, db: Session = Depends(get_db)):
    """Get the latest AI note for a stock symbol."""
    symbol = symbol.upper()
    note = (
        db.query(AiNote)
        .filter(AiNote.symbol == symbol)
        .order_by(AiNote.generated_at.desc())
        .first()
    )
    if not note:
        raise HTTPException(
            status_code=404,
            detail=f"No AI note found for {symbol}. Use POST /api/ai/notes/{symbol}/refresh to generate one.",
        )
    return note


@router.post("/notes/{symbol}/refresh", response_model=AiNoteOut, status_code=201)
def refresh_ai_note(symbol: str, db: Session = Depends(get_db)):
    """Generate (or regenerate) an AI analysis note for a stock symbol."""
    symbol = symbol.upper()

    # Symbol must be watched
    stock = db.query(WatchedStock).filter(WatchedStock.symbol == symbol, WatchedStock.active == True).first()  # noqa: E712
    if not stock:
        raise HTTPException(
            status_code=404,
            detail=f"{symbol} is not in the watch list. Add it first via POST /api/stocks.",
        )

    stock_info = fetch_stock_info(symbol)
    recent_prices = query_latest_prices(symbol, limit=30)

    note_text = generate_ai_note(symbol, stock_info, recent_prices)

    note = AiNote(
        symbol=symbol,
        note=note_text,
        generated_at=datetime.now(timezone.utc),
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/notes", response_model=list[AiNoteOut])
def list_all_notes(db: Session = Depends(get_db)):
    """Get the latest AI note for each watched stock."""
    stocks = db.query(WatchedStock).filter(WatchedStock.active == True).all()  # noqa: E712
    results = []
    for stock in stocks:
        note = (
            db.query(AiNote)
            .filter(AiNote.symbol == stock.symbol)
            .order_by(AiNote.generated_at.desc())
            .first()
        )
        if note:
            results.append(note)
    return results
