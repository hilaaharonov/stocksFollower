"""Application settings loaded from environment variables or a .env file."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Comma-separated list of stock ticker symbols to watch.
    # Example: AAPL,MSFT,GOOGL,AMZN,TSLA
    watched_stocks: str = "AAPL,MSFT,GOOGL"

    class Config:
        env_file = ".env"


settings = Settings()
