import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_URL: str = os.getenv(
        "DB_URL",
        "sqlite:///./data/app.db" 
    )
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")
    ENV: str = os.getenv("APP_ENV", "local")
    SEED_TOKEN: str = os.getenv("SEED_TOKEN", "")
    SEED_ON_START: str = os.getenv("SEED_ON_START", "false")

settings = Settings()
