"""ORM model and repository for user Query records."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional, Sequence

from sqlalchemy import DateTime, Float, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from lios.database.connection import Base, AsyncSession
from lios.utils.helpers import utcnow


class QueryORM(Base):
    __tablename__ = "queries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_answer: Mapped[Optional[str]] = mapped_column(Text)
    consensus_score: Mapped[Optional[float]] = mapped_column(Float)
    decay_score: Mapped[Optional[float]] = mapped_column(Float)
    conflict_flags: Mapped[Optional[str]] = mapped_column(Text)   # JSON array
    citations: Mapped[Optional[str]] = mapped_column(Text)        # JSON array
    agent_responses: Mapped[Optional[str]] = mapped_column(Text)  # JSON object
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    # ── Helpers ───────────────────────────────────────────────────────────────
    def set_conflict_flags(self, flags: list[str]) -> None:
        self.conflict_flags = json.dumps(flags)

    def get_conflict_flags(self) -> list[str]:
        return json.loads(self.conflict_flags) if self.conflict_flags else []

    def set_citations(self, citations: list[dict[str, Any]]) -> None:
        self.citations = json.dumps(citations)

    def get_citations(self) -> list[dict[str, Any]]:
        return json.loads(self.citations) if self.citations else []

    def set_agent_responses(self, responses: dict[str, Any]) -> None:
        self.agent_responses = json.dumps(responses)

    def get_agent_responses(self) -> dict[str, Any]:
        return json.loads(self.agent_responses) if self.agent_responses else {}


class QueryRepository:
    """CRUD operations for Query records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, query: QueryORM) -> QueryORM:
        self._session.add(query)
        await self._session.commit()
        await self._session.refresh(query)
        return query

    async def get_by_id(self, query_id: str) -> Optional[QueryORM]:
        result = await self._session.execute(
            select(QueryORM).where(QueryORM.id == query_id)
        )
        return result.scalar_one_or_none()

    async def list_recent(self, limit: int = 20) -> Sequence[QueryORM]:
        result = await self._session.execute(
            select(QueryORM).order_by(QueryORM.created_at.desc()).limit(limit)
        )
        return result.scalars().all()
