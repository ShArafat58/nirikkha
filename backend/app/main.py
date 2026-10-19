"""Nirikkha backend - FastAPI entry point."""

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_VERSION = "0.1.0"
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Settings loaded from environment variables or backend/.env."""

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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

app = FastAPI(
    title="Nirikkha API",
    version=APP_VERSION,
    description="Governance Crash-Test AI - Trust less, Verify more.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.api_route("/", methods=["GET", "HEAD"])
def root() -> dict:
    return {"app": settings.app_name, "message": "See /docs for the API.", "health": "/health"}


@app.api_route("/health", methods=["GET", "HEAD"])
def health() -> dict:
    """Liveness check. Reports which providers are configured, never the secrets."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": APP_VERSION,
        "env": settings.app_env,
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "providers_configured": {
            "groq": bool(settings.groq_api_key),
            "gemini": bool(settings.gemini_api_key),
            "neo4j": bool(settings.neo4j_uri),
        },
    }