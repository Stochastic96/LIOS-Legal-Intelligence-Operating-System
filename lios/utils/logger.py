"""Structured logging for LIOS using Python's standard library + rich."""

from __future__ import annotations

import logging
import sys

from rich.logging import RichHandler

from lios.config import settings


def get_logger(name: str) -> logging.Logger:
    """Return a named logger configured for LIOS."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logger.setLevel(level)

    handler = RichHandler(
        rich_tracebacks=True,
        markup=True,
        show_path=False,
    )
    handler.setLevel(level)
    logger.addHandler(handler)
    return logger
