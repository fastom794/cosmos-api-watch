from pydantic_settings import BaseSettings

APP_VERSION = "0.1.0"

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://cosmos:cosmos@db:5432/cosmos"

    class Config:
        env_file = ".env"


settings = Settings()

