from pydantic_settings import BaseSettings

from cosmos_api_watch.__version__ import __version__

APP_VERSION = __version__

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://cosmos:cosmos@db:5432/cosmos"
    check_interval_seconds: int = 300
    batch_limit: int = 500
    request_timeout: float = 5.0

    model_config = {
        "env_file": ".env",
        "extra": "ignore"  # Ignore extra environment variables
    }


settings = Settings()

