"""Application-wide configuration loaded from environment / .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LIOS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────────────────────
    env: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # ── Database ──────────────────────────────────────────────────────────────
    db_path: Path = Path("data/db/lios.db")

    # ── Vector Store ─────────────────────────────────────────────────────────
    vector_store_path: Path = Path("data/vector_store")
    embedding_model: str = "all-MiniLM-L6-v2"

    # ── LLM Provider ─────────────────────────────────────────────────────────
    llm_provider: str = "ollama"           # "ollama" | "openai"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"
    openai_api_key: str = ""

    # ── Knowledge Base ────────────────────────────────────────────────────────
    regulations_path: Path = Path("data/regulations")
    eurlex_base_url: str = "https://eur-lex.europa.eu"
    decay_threshold_days: int = 365

    # ── Consensus Engine ─────────────────────────────────────────────────────
    consensus_threshold: float = 0.67

    # ── Derived helpers ───────────────────────────────────────────────────────
    @field_validator("db_path", "vector_store_path", "regulations_path", mode="before")
    @classmethod
    def _ensure_path(cls, v: object) -> Path:
        p = Path(str(v))
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
