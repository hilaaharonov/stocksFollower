# StocksFollower

A self-hosted stock-tracking platform that:
- **Fetches** OHLCV stock data (via yfinance) on a configurable schedule and stores it in **InfluxDB** for long-term retention
- **Visualises** data in **Grafana** dashboards (pre-provisioned, Grafana-like graphs)
- Exposes a **REST API** to add custom Python **scripts/alerts** that analyse stock movements
- Generates **AI notes** on watched stocks (uses OpenAI when a key is configured, falls back to rule-based analysis)

---

## Quick Start

### Prerequisites
- Docker & Docker Compose

### 1. Configure environment

```bash
cp .env.example .env
# (Optional) set OPENAI_API_KEY in .env for AI-powered notes
```

### 2. Start all services

```bash
docker compose up -d
```

| Service  | URL                        | Credentials          |
|----------|----------------------------|----------------------|
| API docs | http://localhost:8000/docs  | –                    |
| Grafana  | http://localhost:3000       | admin / admin         |
| InfluxDB | http://localhost:8086       | admin / adminpassword |

---

## API Overview

### Stocks

| Method   | Path                         | Description                                  |
|----------|------------------------------|----------------------------------------------|
| `GET`    | `/api/stocks`                | List watched stocks                          |
| `POST`   | `/api/stocks`                | Add a stock to the watch list                |
| `DELETE` | `/api/stocks/{symbol}`       | Remove a stock                               |
| `GET`    | `/api/stocks/{symbol}/data`  | Query stored OHLCV data from InfluxDB        |
| `POST`   | `/api/stocks/{symbol}/fetch` | Manually trigger a historical data backfill  |

### Scripts & Alerts

| Method   | Path                           | Description                          |
|----------|--------------------------------|--------------------------------------|
| `GET`    | `/api/scripts`                 | List scripts                         |
| `POST`   | `/api/scripts`                 | Create a new analysis script         |
| `PUT`    | `/api/scripts/{id}`            | Update a script                      |
| `DELETE` | `/api/scripts/{id}`            | Delete a script                      |
| `POST`   | `/api/scripts/{id}/run`        | Manually run a script                |
| `GET`    | `/api/alerts`                  | List triggered alerts                |
| `POST`   | `/api/alerts/{id}/acknowledge` | Acknowledge an alert                 |

### AI Notes

| Method | Path                             | Description                           |
|--------|----------------------------------|---------------------------------------|
| `GET`  | `/api/ai/notes/{symbol}`         | Get latest AI note for a symbol       |
| `POST` | `/api/ai/notes/{symbol}/refresh` | Generate / refresh AI note            |
| `GET`  | `/api/ai/notes`                  | Get latest notes for all watched stocks |

---

## Writing Analysis Scripts

Scripts are plain Python snippets that receive a `context` dict with current
stock data and can append messages to `context['alerts']`.

**Available context keys:** `symbol`, `open`, `high`, `low`, `close`, `volume`

**Example – alert when daily drop exceeds 5 %:**

```python
if context.get('close') and context.get('open'):
    change_pct = (context['close'] - context['open']) / context['open'] * 100
    if change_pct < -5:
        context['alerts'].append(
            f"{context['symbol']} dropped {change_pct:.2f}% today!"
        )
```

Create the script via the API:

```bash
curl -X POST http://localhost:8000/api/scripts \
  -H "Content-Type: application/json" \
  -d '{
    "name": "5% Drop Alert",
    "symbol": "AAPL",
    "code": "if context.get(\"close\") and context.get(\"open\"):\n    pct = (context[\"close\"] - context[\"open\"]) / context[\"open\"] * 100\n    if pct < -5:\n        context[\"alerts\"].append(f\"Dropped {pct:.2f}%\")"
  }'
```

Scripts run automatically at every scheduled fetch. You can also trigger them
manually with `POST /api/scripts/{id}/run`.

---

## Grafana Dashboard

A pre-provisioned **StocksFollower** dashboard is available at
`http://localhost:3000` (folder *Stocks*) immediately after startup.

The dashboard includes:
- **Close Price** time-series panel (multi-symbol, filterable via template variable)
- **Volume** bar chart

Use the **Symbol** template variable at the top to toggle which stocks are displayed.

---

## Development

```bash
cd backend
pip install -r requirements.txt
# Run locally (connects to a local InfluxDB)
uvicorn main:app --reload
# Run tests
pytest tests/ -v
```
