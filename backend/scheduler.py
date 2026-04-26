"""Background scheduler: periodically fetches stock prices and runs scripts."""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal, WatchedStock, Script, Alert
from services.stock_fetcher import fetch_latest_price, fetch_stock_info
from services.influxdb_writer import write_price_point
from services.script_executor import run_script

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def _fetch_and_store_all() -> None:
    """Fetch latest prices for all active watched stocks and run scripts."""
    db: Session = SessionLocal()
    try:
        stocks = db.query(WatchedStock).filter(WatchedStock.active == True).all()  # noqa: E712
        for stock in stocks:
            symbol = stock.symbol
            price_data = fetch_latest_price(symbol)
            if price_data is None:
                continue

            # Write to InfluxDB
            write_price_point(price_data)

            # Run enabled scripts for this symbol (global + symbol-specific)
            scripts = (
                db.query(Script)
                .filter(
                    Script.enabled == True,  # noqa: E712
                    (Script.symbol == None) | (Script.symbol == symbol),  # noqa: E711
                )
                .all()
            )
            for script in scripts:
                alerts = run_script(script.code, price_data)
                for msg in alerts:
                    alert = Alert(
                        script_id=script.id,
                        symbol=symbol,
                        message=msg,
                        triggered_at=datetime.now(timezone.utc),
                    )
                    db.add(alert)
            db.commit()
    except Exception as exc:
        logger.error("Scheduler job error: %s", exc)
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> None:
    scheduler.add_job(
        _fetch_and_store_all,
        "interval",
        seconds=settings.fetch_interval_seconds,
        id="fetch_stocks",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started with interval=%ds", settings.fetch_interval_seconds)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
