"""Application settings, loaded from environment variables or backend/.env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Nirikkha"
    app_env: str = "development"
    # Comma-separated list of allowed frontend origins.
    cors_origins: str = "http://localhost:3000"

    groq_api_key: str = ""
    gemini_api_key: str = ""

    neo4j_uri: str = ""
    neo4j_username: str = ""
    neo4j_password: str = ""
    neo4j_database: str = ""

    # SEC requires a User-Agent with a real name and email.
    sec_user_agent: str = ""

    # Local download cache (not committed).
    cache_dir: Path = BACKEND_DIR / ".cache"


@lru_cache
def get_settings() -> Settings:
    return Settings()