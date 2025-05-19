from functools import lru_cache
from typing import Optional
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    # Database settings
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "Lmp61430")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "faceDetection")

    # JWT settings
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", "83daa0256a2289b0fb23693bf1f6034d44396675749244721a2b20e896e11662"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings():
    return Settings()
