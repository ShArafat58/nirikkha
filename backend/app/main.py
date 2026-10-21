"""Nirikkha backend - FastAPI entry point."""

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.analytics.warehouse import resolve_db
from app.api.routes import router as api_router
from app.admin.routes import router as admin_router
from app.auth.routes import router as auth_router
from app.business.routes import router as billing_router
from app.config import get_settings
from app.api.replay_routes import router as replay_router
from app.api.radar_routes import router as radar_router
from app.api.graph_routes import router as graph_router
from app.api.help import router as help_router

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
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(billing_router)
app.include_router(replay_router)
app.include_router(radar_router)
app.include_router(graph_router)
app.include_router(help_router)

def _memory_mb() -> float | None:
    """Resident memory of this process on Linux (Render); None elsewhere."""
    try:
        with open("/proc/self/status", encoding="ascii") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return round(int(line.split()[1]) / 1024, 1)
    except OSError:
        return None
    return None

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
        "memory_mb": _memory_mb(),
        "warehouse_snapshot": resolve_db(settings.cache_dir) is not None,
        "rerank_enabled": settings.rerank_enabled,
        "providers_configured": {
            "groq": bool(settings.groq_api_key),
            "gemini": bool(settings.gemini_api_key),
            "neo4j": bool(settings.neo4j_uri),
            "supabase": bool(settings.supabase_db_url),
        },
    }