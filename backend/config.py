from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    influxdb_url: str = "http://localhost:8086"
    influxdb_token: str = "my-super-secret-admin-token"
    influxdb_org: str = "stocks"
    influxdb_bucket: str = "stocks"

    openai_api_key: str = ""

    fetch_interval_seconds: int = 300

    database_url: str = "sqlite:///./stocks_meta.db"

    class Config:
        env_file = ".env"


settings = Settings()
