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
    LLM_ENABLED: bool = False
    LLM_PROVIDER: str = "openai_compatible"  # openai_compatible | azure
    LLM_BASE_URL: str = "http://localhost:11434/v1"
    LLM_MODEL: str = "llama3"
    LLM_API_KEY: str = "ollama"
    LLM_TIMEOUT_SECONDS: int = 30

    # Azure OpenAI settings (used when LLM_PROVIDER=azure)
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-02-01"
    AZURE_OPENAI_DEPLOYMENT: str = ""

    # Consensus settings
    CONSENSUS_THRESHOLD: int = 2  # out of 3 agents must agree

    # Chat orchestration mode
    CHAT_MODE: str = "simple"  # simple | consensus

    def __post_init__(self) -> None:
        # Allow environment variable overrides
        self.LLM_ENABLED = os.environ.get("LIOS_LLM_ENABLED", "false").lower() == "true"
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


settings = Settings()
