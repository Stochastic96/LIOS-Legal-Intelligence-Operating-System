"""ORM model and repository for Regulation records."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import DateTime, Index, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from lios.database.connection import Base, AsyncSession
from lios.utils.helpers import utcnow


class RegulationORM(Base):
    __tablename__ = "regulations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    short_name: Mapped[str] = mapped_column(String(64), nullable=False)
    framework: Mapped[str] = mapped_column(String(64), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(64), nullable=False, default="EU")
    article_ref: Mapped[Optional[str]] = mapped_column(String(128))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    version: Mapped[str] = mapped_column(String(32), default="1.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    __table_args__ = (
        Index("idx_regulations_framework", "framework"),
        Index("idx_regulations_jurisdiction", "jurisdiction"),
    )


class RegulationRepository:
    """CRUD operations for Regulation records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, regulation: RegulationORM) -> RegulationORM:
        self._session.add(regulation)
        await self._session.commit()
        await self._session.refresh(regulation)
        return regulation

    async def get_by_id(self, regulation_id: str) -> Optional[RegulationORM]:
        result = await self._session.execute(
            select(RegulationORM).where(RegulationORM.id == regulation_id)
        )
        return result.scalar_one_or_none()

    async def list_by_framework(self, framework: str) -> Sequence[RegulationORM]:
        result = await self._session.execute(
            select(RegulationORM).where(RegulationORM.framework == framework)
        )
        return result.scalars().all()

    async def list_all(self) -> Sequence[RegulationORM]:
        result = await self._session.execute(select(RegulationORM))
        return result.scalars().all()

    async def update(self, regulation: RegulationORM) -> RegulationORM:
        regulation.updated_at = utcnow()
        await self._session.commit()
        await self._session.refresh(regulation)
        return regulation

    async def delete(self, regulation_id: str) -> bool:
        obj = await self.get_by_id(regulation_id)
        if obj is None:
            return False
        await self._session.delete(obj)
        await self._session.commit()
        return True
