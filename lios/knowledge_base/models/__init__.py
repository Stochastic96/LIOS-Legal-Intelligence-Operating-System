"""Pydantic models for regulatory documents."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class Framework(str, Enum):
    CSRD = "CSRD"
    ESRS = "ESRS"
    EU_TAXONOMY = "EU_TAXONOMY"
    SFDR = "SFDR"
    CSDDD = "CSDDD"       # Corporate Sustainability Due Diligence Directive
    CBAM = "CBAM"         # Carbon Border Adjustment Mechanism
    OTHER = "OTHER"


class Regulation(BaseModel):
    """A single regulatory document or article chunk."""

    id: str
    title: str
    short_name: str
    framework: Framework
    jurisdiction: str = "EU"
    article_ref: Optional[str] = None
    content: str
    source_url: Optional[str] = None
    published_at: Optional[datetime] = None
    last_verified_at: Optional[datetime] = None
    version: str = "1.0"


class RegulationChunk(BaseModel):
    """A text chunk derived from a Regulation, ready for embedding."""

    chunk_id: str
    regulation_id: str
    framework: Framework
    article_ref: Optional[str]
    text: str
    char_start: int
    char_end: int
