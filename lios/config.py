"""Configuration for LIOS."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    APP_NAME: str = "LIOS"
    VERSION: str = "0.1.0"
    LOG_LEVEL: str = "INFO"

    # LLM backend (optional)
    LLM_ENABLED: bool = True
    LLM_PROVIDER: str = "openai_compatible"  # openai_compatible | azure
    LLM_BASE_URL: str = "http://localhost:11434/v1"
    LLM_MODEL: str = "mistral:latest"
    LLM_API_KEY: str = "ollama"
    LLM_TIMEOUT_SECONDS: int = 120

    # Azure OpenAI settings (used when LLM_PROVIDER=azure)
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-02-01"
    AZURE_OPENAI_DEPLOYMENT: str = ""

    # Consensus settings
    CONSENSUS_THRESHOLD: int = 2  # agents that must agree (out of total)

    # Chat orchestration mode
    CHAT_MODE: str = "simple"  # simple | consensus

    # Security – API key authentication
    # Set LIOS_API_KEY to a non-empty string to require the X-API-Key header.
    API_KEY: str = ""
    API_KEY_REQUIRED: bool = False

    # CORS – comma-separated list of allowed origins ("*" to allow all)
    CORS_ALLOWED_ORIGINS: str = "*"

    # Developer mode – exposes /debug/routes and extra diagnostics
    DEV_MODE: bool = False

    # Chat store backend: "jsonl" (default) or "sqlite"
    CHAT_STORE_BACKEND: str = "jsonl"
    CHAT_STORE_PATH: str = "logs/chat_training.jsonl"
    CHAT_STORE_DB_PATH: str = "logs/chat_training.db"

    def __post_init__(self) -> None:
        # Allow environment variable overrides
        self.LLM_ENABLED = os.environ.get("LIOS_LLM_ENABLED", "true").lower() == "true"
        self.LLM_PROVIDER = os.environ.get("LIOS_LLM_PROVIDER", self.LLM_PROVIDER)
        self.LLM_BASE_URL = os.environ.get("LIOS_LLM_BASE_URL", self.LLM_BASE_URL)
        self.LLM_MODEL = os.environ.get("LIOS_LLM_MODEL", self.LLM_MODEL)
        self.LLM_API_KEY = os.environ.get("LIOS_LLM_API_KEY", self.LLM_API_KEY)
        self.LLM_TIMEOUT_SECONDS = int(
            os.environ.get("LIOS_LLM_TIMEOUT_SECONDS", str(self.LLM_TIMEOUT_SECONDS))
        )

        self.AZURE_OPENAI_ENDPOINT = os.environ.get(
            "LIOS_AZURE_OPENAI_ENDPOINT", self.AZURE_OPENAI_ENDPOINT
        )
        self.AZURE_OPENAI_API_KEY = os.environ.get(
            "LIOS_AZURE_OPENAI_API_KEY", self.AZURE_OPENAI_API_KEY
        )
        self.AZURE_OPENAI_API_VERSION = os.environ.get(
            "LIOS_AZURE_OPENAI_API_VERSION", self.AZURE_OPENAI_API_VERSION
        )
        self.AZURE_OPENAI_DEPLOYMENT = os.environ.get(
            "LIOS_AZURE_OPENAI_DEPLOYMENT", self.AZURE_OPENAI_DEPLOYMENT
        )
        self.LOG_LEVEL = os.environ.get("LIOS_LOG_LEVEL", self.LOG_LEVEL)
        self.CHAT_MODE = os.environ.get("LIOS_CHAT_MODE", self.CHAT_MODE).lower()

        self.API_KEY = os.environ.get("LIOS_API_KEY", self.API_KEY)
        self.API_KEY_REQUIRED = (
            os.environ.get("LIOS_API_KEY_REQUIRED", "").lower() == "true"
            or bool(self.API_KEY)
        )
        self.CORS_ALLOWED_ORIGINS = os.environ.get(
            "LIOS_CORS_ALLOWED_ORIGINS", self.CORS_ALLOWED_ORIGINS
        )
        self.DEV_MODE = os.environ.get("LIOS_DEV_MODE", "false").lower() == "true"
        self.CHAT_STORE_BACKEND = os.environ.get(
            "LIOS_CHAT_STORE_BACKEND", self.CHAT_STORE_BACKEND
        ).lower()
        self.CHAT_STORE_PATH = os.environ.get("LIOS_CHAT_STORE_PATH", self.CHAT_STORE_PATH)
        self.CHAT_STORE_DB_PATH = os.environ.get(
            "LIOS_CHAT_STORE_DB_PATH", self.CHAT_STORE_DB_PATH
        )

    @property
    def cors_origins(self) -> list[str]:
        """Return CORS allowed origins as a list."""
        return [o.strip() for o in self.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]


settings = Settings()
