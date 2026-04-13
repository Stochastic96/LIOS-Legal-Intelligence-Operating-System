"""Shared pytest fixtures."""

from __future__ import annotations

import asyncio
import pytest
from httpx import AsyncClient, ASGITransport

from lios.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for the whole test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client():
    """Async HTTPX test client for the FastAPI app."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
