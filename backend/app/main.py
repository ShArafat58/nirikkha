"""Nirikkha backend - FastAPI entry point."""

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.config import get_settings

APP_VERSION = "0.1.0"

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

app.include_router(api_router)


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
            "supabase": bool(settings.supabase_db_url),
        },
    }