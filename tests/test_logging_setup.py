"""Tests for logging setup behavior and shutdown safety."""

from __future__ import annotations

import logging
from io import StringIO

from lios.logging_setup import SafeStreamHandler, setup_logging


def test_safe_stream_handler_ignores_closed_stream() -> None:
    """Emitting on a closed stream should not raise and should be ignored."""
    stream = StringIO()
    handler = SafeStreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(message)s"))

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )

    stream.close()
    handler.emit(record)


def test_setup_logging_uses_safe_stream_handler() -> None:
    """Root logger should include the custom safe console handler."""
    setup_logging(log_level="INFO")
    root_logger = logging.getLogger()
    assert any(isinstance(h, SafeStreamHandler) for h in root_logger.handlers)
