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
    # Local LLM runtime (optional; used as last fallback when reachable)
    ollama_url: str = "http://localhost:11434"

    neo4j_uri: str = ""
    neo4j_username: str = ""
    neo4j_password: str = ""
    neo4j_database: str = ""

    # Supabase Postgres (Session pooler URI, port 5432). Never commit.
    supabase_db_url: str = ""

    # SEC requires a User-Agent with a real name and email.
    sec_user_agent: str = ""

    # Retrieval embeddings.
    # "local" (default): BAAI/bge-small-en-v1.5 via fastembed, 384 dims, unlimited, data stays on the machine.
    # "gemini": gemini-embedding-001 (free tier: 1,000 requests/day/project), set EMBEDDING_DIM=768.
    embedding_provider: str = "local"
    local_embedding_model: str = "BAAI/bge-small-en-v1.5"
    # Cross-encoder reranker (local, fastembed) and how many hybrid candidates it re-scores.
    reranker_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    rerank_candidates: int = 20
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768
    gemini_embed_tpm: int = 25000
    gemini_embed_rpm: int = 90

    # Local download / processing cache (not committed).
    cache_dir: Path = BACKEND_DIR / ".cache"


@lru_cache
def get_settings() -> Settings:
    return Settings()