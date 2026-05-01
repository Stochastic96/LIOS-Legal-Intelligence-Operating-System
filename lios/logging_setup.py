"""Logging configuration and utilities for LIOS."""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from lios.config import settings


class SafeStreamHandler(logging.StreamHandler):
    """StreamHandler that ignores writes attempted after the stream is closed."""

    def handleError(self, record: logging.LogRecord) -> None:  # noqa: N802
        exc = sys.exc_info()[1]
        if isinstance(exc, ValueError) and "closed file" in str(exc).lower():
            return
        super().handleError(record)


class StructuredFormatter(logging.Formatter):
    """Format logs as JSON for better parsing and analysis."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(log_data)


class PlainFormatter(logging.Formatter):
    """Human-readable formatter for console output."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as readable text with colors."""
        if sys.stdout.isatty():
            levelname = record.levelname
            color = self.COLORS.get(levelname, "")
            reset = self.COLORS["RESET"]
            colored_level = f"{color}{levelname}{reset}"
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            return f"{timestamp} | {colored_level} | {record.name} | {record.getMessage()}"
        else:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            return f"{timestamp} | {record.levelname} | {record.name} | {record.getMessage()}"


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path | str] = None,
    json_format: bool = False,
) -> None:
    """Configure logging for the entire application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for file logging
        json_format: If True, use JSON format; if False, use plain format
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = SafeStreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    formatter = StructuredFormatter() if json_format else PlainFormatter()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Prevent debug noise from third-party HTTP libraries at interpreter shutdown.
    logging.getLogger("httpcore").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.INFO)

    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
        )
        file_handler.setLevel(log_level)
        formatter = StructuredFormatter()  # Always JSON for files
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.LoggerAdapter:
    """Get a logger with context support for request tracking.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger adapter
    """
    logger = logging.getLogger(name)
    return logging.LoggerAdapter(logger, {})


class RequestLogger:
    """Context manager for logging and timing requests."""

    def __init__(self, logger: logging.LoggerAdapter, action: str, **context: Any):
        """Initialize request logger.

        Args:
            logger: Logger instance
            action: Description of the action being logged
            **context: Additional context to include in logs
        """
        self.logger = logger
        self.action = action
        self.context = context
        self.start_time = None

    def __enter__(self):
        """Log the start of an operation."""
        import time

        self.start_time = time.time()
        self.logger.info(f"Starting: {self.action}", extra=self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log the end of an operation, including duration and any errors."""
        import time

        duration_ms = (time.time() - self.start_time) * 1000

        if exc_type is None:
            self.logger.info(
                f"Completed: {self.action}",
                extra={**self.context, "duration_ms": duration_ms},
            )
        else:
            self.logger.error(
                f"Failed: {self.action} - {exc_type.__name__}: {exc_val}",
                exc_info=(exc_type, exc_val, exc_tb),
                extra={**self.context, "duration_ms": duration_ms},
            )

        return False  # Re-raise exception


# Initialize logging on module import
setup_logging(
    log_level=settings.LOG_LEVEL,
    log_file=Path("logs/lios.log"),
    json_format=False,  # Use plain format for console
)

# Module-level logger
logger = get_logger(__name__)
