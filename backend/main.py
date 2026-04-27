"""StocksFollower backend – FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.stocks import router as stocks_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="StocksFollower API",
    description="Real-time stock data API that powers the Grafana dashboard.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks_router)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
