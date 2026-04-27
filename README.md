# StocksFollower

A minimal, self-hosted Grafana dashboard for tracking stock prices in **real-time**.

- **No database** – price data is fetched from [yfinance](https://github.com/ranaroussi/yfinance) on every request and never stored.
- **Grafana** visualises the data through the [Infinity datasource plugin](https://grafana.com/grafana/plugins/yesoreyeram-infinity-datasource/), which calls the backend API directly.
- The **FastAPI backend** is a thin, stateless service; extending it with new endpoints is straightforward.

---

## Quick Start

### Prerequisites
- Docker & Docker Compose

### 1. Configure environment

```bash
cp .env.example .env
# Edit WATCHED_STOCKS to list the symbols you want to follow
```

### 2. Start all services

```bash
docker compose up -d
```

| Service  | URL                       | Credentials |
|----------|---------------------------|-------------|
| API docs | http://localhost:8000/docs | –           |
| Grafana  | http://localhost:3000      | admin / admin |

The Grafana dashboard is pre-provisioned and opens automatically in the **Stocks** folder.

---

## Configuration

| Variable         | Default           | Description                                          |
|------------------|-------------------|------------------------------------------------------|
| `WATCHED_STOCKS` | `AAPL,MSFT,GOOGL` | Comma-separated list of ticker symbols to watch      |

Edit `.env` and restart to change which stocks appear in the dashboard.

---

## API Overview

| Method | Path                              | Description                                         |
|--------|-----------------------------------|-----------------------------------------------------|
| `GET`  | `/api/stocks`                     | List watched symbols (from `WATCHED_STOCKS` config) |
| `GET`  | `/api/stocks/{symbol}/quote`      | Live quote: price, OHLC, volume, currency           |
| `GET`  | `/api/stocks/{symbol}/history`    | Historical OHLCV data (supports `period`/`interval`)|
| `GET`  | `/health`                         | Health check                                        |

### History query parameters

| Parameter  | Default | Examples                              |
|------------|---------|---------------------------------------|
| `period`   | `1mo`   | `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y` |
| `interval` | `1d`    | `1m`, `5m`, `15m`, `30m`, `1h`, `1d`, `1wk`       |

---

## Grafana Dashboard

The pre-provisioned **StocksFollower** dashboard at `http://localhost:3000` includes:

- **Price History** – time-series chart of OHLC prices
- **Volume History** – bar chart of trading volume
- **Live Price / Day High / Day Low / Volume** – stat panels with the latest quote
- **Symbol**, **Period**, and **Interval** dropdown variables at the top

The dashboard auto-refreshes every 5 minutes.

---

## Extending the Project

The backend is organised for easy expansion:

```
backend/
  main.py               # App entry point – register new routers here
  config.py             # Settings from environment variables
  routers/
    stocks.py           # Existing stock endpoints
    your_feature.py     # Add a new router here
  services/
    stock_fetcher.py    # yfinance wrapper
    your_service.py     # Add new service logic here
```

To add a new feature:
1. Create `backend/services/your_service.py` with the business logic.
2. Create `backend/routers/your_feature.py` with the FastAPI routes.
3. Register the router in `backend/main.py` with `app.include_router(...)`.
4. Add new Grafana panels to `grafana/provisioning/dashboards/stocks.json`.

---

## Development

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```
