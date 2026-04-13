"""SQLAlchemy async engine and session factory."""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from lios.config import settings
from lios.utils.logger import get_logger

logger = get_logger(__name__)

DATABASE_URL = f"sqlite+aiosqlite:///{settings.db_path}"

engine = create_async_engine(
    DATABASE_URL,
    echo=(settings.env == "development"),
    connect_args={"check_same_thread": False},
)

AsyncSessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


async def init_db() -> None:
    """Create all tables (idempotent – runs on startup)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialised at %s", settings.db_path)


async def get_session() -> AsyncGenerator[AsyncSession, None]:  # used as a FastAPI dependency
    async with AsyncSessionFactory() as session:
        yield session
