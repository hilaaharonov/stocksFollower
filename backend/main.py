"""StocksFollower backend – FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routers.stocks import router as stocks_router
from routers.scripts import router as scripts_router, alerts_router
from routers.ai_notes import router as ai_router
from scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database …")
    init_db()
    logger.info("Starting background scheduler …")
    start_scheduler()
    yield
    # Shutdown
    logger.info("Stopping scheduler …")
    stop_scheduler()


app = FastAPI(
    title="StocksFollower API",
    description=(
        "Query and store stock data, manage analysis scripts/alerts, "
        "and get AI-powered stock notes."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks_router)
app.include_router(scripts_router)
app.include_router(alerts_router)
app.include_router(ai_router)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
