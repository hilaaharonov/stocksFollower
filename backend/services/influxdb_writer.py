"""InfluxDB writer service for time-series stock data."""

import logging
from datetime import datetime
from typing import Optional

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from config import settings

logger = logging.getLogger(__name__)

_client: Optional[InfluxDBClient] = None
_write_api = None


def get_client() -> InfluxDBClient:
    global _client
    if _client is None:
        _client = InfluxDBClient(
            url=settings.influxdb_url,
            token=settings.influxdb_token,
            org=settings.influxdb_org,
        )
    return _client


def get_write_api():
    global _write_api
    if _write_api is None:
        _write_api = get_client().write_api(write_options=SYNCHRONOUS)
    return _write_api


def write_price_point(data: dict) -> None:
    """Write a single OHLCV data point to InfluxDB."""
    try:
        point = (
            Point("stock_price")
            .tag("symbol", data["symbol"])
            .field("open", data["open"])
            .field("high", data["high"])
            .field("low", data["low"])
            .field("close", data["close"])
            .field("volume", data["volume"])
            .time(data["timestamp"], WritePrecision.SECONDS)
        )
        get_write_api().write(bucket=settings.influxdb_bucket, org=settings.influxdb_org, record=point)
    except Exception as exc:
        logger.error("InfluxDB write error for %s: %s", data.get("symbol"), exc)


def write_price_batch(records: list[dict]) -> None:
    """Write multiple OHLCV data points to InfluxDB."""
    if not records:
        return
    try:
        points = []
        for data in records:
            point = (
                Point("stock_price")
                .tag("symbol", data["symbol"])
                .field("open", data["open"])
                .field("high", data["high"])
                .field("low", data["low"])
                .field("close", data["close"])
                .field("volume", data["volume"])
                .time(data["timestamp"], WritePrecision.SECONDS)
            )
            points.append(point)
        get_write_api().write(bucket=settings.influxdb_bucket, org=settings.influxdb_org, record=points)
        logger.info("Wrote %d points to InfluxDB", len(points))
    except Exception as exc:
        logger.error("InfluxDB batch write error: %s", exc)


def query_latest_prices(symbol: str, limit: int = 100) -> list[dict]:
    """Query the most recent price records for a symbol from InfluxDB."""
    try:
        query_api = get_client().query_api()
        flux = f'''
from(bucket: "{settings.influxdb_bucket}")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "stock_price")
  |> filter(fn: (r) => r.symbol == "{symbol}")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: {limit})
'''
        tables = query_api.query(flux, org=settings.influxdb_org)
        results = []
        for table in tables:
            for record in table.records:
                results.append(
                    {
                        "timestamp": record.get_time(),
                        "open": record.values.get("open"),
                        "high": record.values.get("high"),
                        "low": record.values.get("low"),
                        "close": record.values.get("close"),
                        "volume": record.values.get("volume"),
                    }
                )
        return results
    except Exception as exc:
        logger.error("InfluxDB query error for %s: %s", symbol, exc)
        return []


def close_client() -> None:
    global _client, _write_api
    if _write_api:
        _write_api.close()
        _write_api = None
    if _client:
        _client.close()
        _client = None
