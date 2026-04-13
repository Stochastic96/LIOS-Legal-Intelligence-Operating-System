"""Global exception handler middleware."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from lios.utils.logger import get_logger

logger = get_logger(__name__)


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Check the server logs."},
    )
