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
    LLM_BASE_URL: str = "http://localhost:11434/v1"
    LLM_MODEL: str = "llama3"
    LLM_API_KEY: str = "ollama"

    # Consensus settings
    CONSENSUS_THRESHOLD: int = 2  # out of 3 agents must agree

    def __post_init__(self) -> None:
        # Allow environment variable overrides
        self.LLM_ENABLED = os.environ.get("LIOS_LLM_ENABLED", "false").lower() == "true"
        self.LLM_BASE_URL = os.environ.get("LIOS_LLM_BASE_URL", self.LLM_BASE_URL)
        self.LLM_MODEL = os.environ.get("LIOS_LLM_MODEL", self.LLM_MODEL)
        self.LLM_API_KEY = os.environ.get("LIOS_LLM_API_KEY", self.LLM_API_KEY)
        self.LOG_LEVEL = os.environ.get("LIOS_LOG_LEVEL", self.LOG_LEVEL)


settings = Settings()
