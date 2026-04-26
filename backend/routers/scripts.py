"""Scripts router: manage analysis scripts and alerts."""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import Script, Alert, WatchedStock, get_db
from services.script_executor import run_script, validate_script
from services.influxdb_writer import query_latest_prices
from services.stock_fetcher import fetch_latest_price

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/scripts", tags=["scripts"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ScriptCreate(BaseModel):
    name: str
    description: Optional[str] = None
    code: str
    symbol: Optional[str] = None  # None = apply to all watched stocks
    enabled: bool = True


class ScriptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None
    symbol: Optional[str] = None
    enabled: Optional[bool] = None


class ScriptOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    code: str
    symbol: Optional[str]
    enabled: bool

    class Config:
        from_attributes = True


class AlertOut(BaseModel):
    id: int
    script_id: int
    symbol: str
    message: str
    triggered_at: datetime
    acknowledged: bool

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Script endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[ScriptOut])
def list_scripts(db: Session = Depends(get_db)):
    """List all scripts."""
    return db.query(Script).all()


@router.post("", response_model=ScriptOut, status_code=201)
def create_script(payload: ScriptCreate, db: Session = Depends(get_db)):
    """Create a new analysis script."""
    error = validate_script(payload.code)
    if error:
        raise HTTPException(status_code=422, detail=f"Invalid script: {error}")

    script = Script(
        name=payload.name,
        description=payload.description,
        code=payload.code,
        symbol=payload.symbol.upper() if payload.symbol else None,
        enabled=payload.enabled,
    )
    db.add(script)
    db.commit()
    db.refresh(script)
    return script


@router.put("/{script_id}", response_model=ScriptOut)
def update_script(script_id: int, payload: ScriptUpdate, db: Session = Depends(get_db)):
    """Update an existing script."""
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    if payload.code is not None:
        error = validate_script(payload.code)
        if error:
            raise HTTPException(status_code=422, detail=f"Invalid script: {error}")
        script.code = payload.code

    if payload.name is not None:
        script.name = payload.name
    if payload.description is not None:
        script.description = payload.description
    if payload.symbol is not None:
        script.symbol = payload.symbol.upper()
    if payload.enabled is not None:
        script.enabled = payload.enabled

    script.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(script)
    return script


@router.delete("/{script_id}", status_code=204)
def delete_script(script_id: int, db: Session = Depends(get_db)):
    """Delete a script."""
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    db.delete(script)
    db.commit()


@router.post("/{script_id}/run")
def run_script_now(
    script_id: int,
    symbol: Optional[str] = Query(default=None, description="Override target symbol"),
    db: Session = Depends(get_db),
):
    """Manually run a script against current stock data."""
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    target_symbol = (symbol or script.symbol or "").upper()
    if not target_symbol:
        # Run against all watched stocks
        stocks = db.query(WatchedStock).filter(WatchedStock.active == True).all()  # noqa: E712
        results = []
        for stock in stocks:
            price_data = fetch_latest_price(stock.symbol)
            if price_data is None:
                continue
            alerts = run_script(script.code, price_data)
            _save_alerts(db, script_id, stock.symbol, alerts)
            results.append({"symbol": stock.symbol, "alerts": alerts})
        return {"ran_on": [r["symbol"] for r in results], "results": results}

    price_data = fetch_latest_price(target_symbol)
    if price_data is None:
        raise HTTPException(status_code=502, detail=f"Could not fetch data for {target_symbol}")

    alerts = run_script(script.code, price_data)
    _save_alerts(db, script_id, target_symbol, alerts)
    return {"symbol": target_symbol, "alerts": alerts}


def _save_alerts(db: Session, script_id: int, symbol: str, messages: list[str]) -> None:
    for msg in messages:
        db.add(Alert(script_id=script_id, symbol=symbol, message=msg,
                     triggered_at=datetime.now(timezone.utc)))
    db.commit()


# ---------------------------------------------------------------------------
# Alert endpoints
# ---------------------------------------------------------------------------


alerts_router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@alerts_router.get("", response_model=list[AlertOut])
def list_alerts(
    symbol: Optional[str] = Query(default=None),
    unacknowledged_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List triggered alerts."""
    query = db.query(Alert)
    if symbol:
        query = query.filter(Alert.symbol == symbol.upper())
    if unacknowledged_only:
        query = query.filter(Alert.acknowledged == False)  # noqa: E712
    return query.order_by(Alert.triggered_at.desc()).limit(limit).all()


@alerts_router.post("/{alert_id}/acknowledge", status_code=200)
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    """Acknowledge an alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged = True
    db.commit()
    return {"acknowledged": True}
