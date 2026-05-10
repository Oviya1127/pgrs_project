"""Application configuration settings."""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # -----------------------------
    # DATABASE (NO DEFAULTS)
    # -----------------------------
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    # -----------------------------
    # SECURITY
    # -----------------------------
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # -----------------------------
    # CLOUDINARY (optional)
    # -----------------------------
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # -----------------------------
    # APP INFO
    # -----------------------------
    APP_NAME: str = "Smart Public Grievance Redressal System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # -----------------------------
    # ENV FILE (LOCAL DEV ONLY)
    # -----------------------------
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    # -----------------------------
    # DATABASE URL BUILDER
    # -----------------------------
    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:"
            f"{self.DB_PASSWORD}@{self.DB_HOST}:"
            f"{self.DB_PORT}/{self.DB_NAME}"
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()