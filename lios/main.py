"""LIOS entry point – exposes FastAPI app and Click CLI."""

from lios.api.routes import app
from lios.cli.interface import cli

__all__ = ["app", "cli"]
