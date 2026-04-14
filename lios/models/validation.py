"""Pydantic models for input validation and request/response handling."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


class CompanyProfile(BaseModel):
    """Validated company profile data."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "employees": 750,
            "turnover_eur": 350_000_000,
            "balance_sheet_eur": 200_000_000,
            "listed": True,
            "jurisdiction": "Germany",
        }
    })

    employees: int = Field(
        default=0,
        ge=0,
        le=1_000_000,
        description="Number of employees (0-1,000,000)",
    )
    turnover_eur: float = Field(
        default=0.0,
        ge=0,
        le=1_000_000_000_000,
        description="Annual turnover in EUR (0-1 trillion)",
    )
    balance_sheet_eur: float = Field(
        default=0.0,
        ge=0,
        le=1_000_000_000_000,
        description="Total balance sheet in EUR (0-1 trillion)",
    )
    listed: bool = Field(
        default=False,
        description="Is the company listed on a regulated market?",
    )
    jurisdiction: Optional[str] = Field(
        default=None,
        description="Primary jurisdiction (e.g., 'Germany', 'France')",
    )

    @field_validator("employees")
    @classmethod
    def validate_employees(cls, v: int) -> int:
        """Ensure employees is reasonable."""
        if v > 1_000_000:
            raise ValueError("Employee count exceeds 1 million (unrealistic)")
        return v

    @field_validator("turnover_eur")
    @classmethod
    def validate_turnover(cls, v: float) -> float:
        """Ensure turnover is reasonable."""
        if v > 1_000_000_000_000:
            raise ValueError("Turnover exceeds 1 trillion EUR")
        return v

    @field_validator("balance_sheet_eur")
    @classmethod
    def validate_balance_sheet(cls, v: float) -> float:
        """Ensure balance sheet is reasonable."""
        if v > 1_000_000_000_000:
            raise ValueError("Balance sheet exceeds 1 trillion EUR")
        return v


class QueryRequest(BaseModel):
    """Validated query request."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "query": "What are the ESG reporting requirements for large companies?",
            "company_profile": {
                "employees": 1500,
                "turnover_eur": 500_000_000,
                "balance_sheet_eur": 350_000_000,
                "listed": True,
                "jurisdiction": "Germany",
            },
            "jurisdictions": ["EU", "Germany"],
        }
    })

    query: str = Field(
        ...,
        min_length=3,
        max_length=5000,
        description="The legal question or query (3-5000 characters)",
    )
    company_profile: Optional[CompanyProfile] = Field(
        default=None,
        description="Optional company profile for context-aware responses",
    )
    jurisdictions: Optional[list[str]] = Field(
        default=None,
        max_length=10,
        description="List of jurisdictions to consider (max 10)",
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Ensure query is not just whitespace."""
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace-only")
        return v.strip()

    @field_validator("jurisdictions")
    @classmethod
    def validate_jurisdictions(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Ensure jurisdictions are valid and not duplicated."""
        if v is None:
            return v
        unique_jurs = list(dict.fromkeys(jur.upper() for jur in v))
        if len(unique_jurs) != len(v):
            raise ValueError("Jurisdictions contain duplicates")
        return unique_jurs


class ApplicabilityRequest(BaseModel):
    """Validated applicability check request."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "regulation": "CSRD",
            "company_profile": {
                "employees": 600,
                "turnover_eur": 300_000_000,
                "balance_sheet_eur": 150_000_000,
                "listed": False,
            },
        }
    })

    regulation: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Regulation name to check (e.g., 'CSRD', 'ESRS')",
    )
    company_profile: CompanyProfile = Field(
        ..., description="Company profile for applicability check"
    )

    @field_validator("regulation")
    @classmethod
    def validate_regulation(cls, v: str) -> str:
        """Normalize regulation name."""
        return v.upper().strip()


class RoadmapRequest(BaseModel):
    """Validated compliance roadmap request."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "company_profile": {
                "employees": 2000,
                "turnover_eur": 800_000_000,
                "balance_sheet_eur": 500_000_000,
                "listed": True,
            },
            "regulations": ["CSRD", "ESRS"],
        }
    })

    company_profile: CompanyProfile = Field(
        ..., description="Company profile for roadmap generation"
    )
    regulations: Optional[list[str]] = Field(
        default=None,
        max_length=10,
        description="Specific regulations to include (defaults to all applicable)",
    )


class DecayScoreResponse(BaseModel):
    """Response model for decay score."""

    regulation: str
    score: int = Field(..., ge=0, le=100)
    freshness_label: str
    days_since_update: int
    last_updated: str


class CitationResponse(BaseModel):
    """Response model for a citation."""

    regulation: str
    article_id: str
    title: str
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    url: Optional[str] = None


class ConflictResponse(BaseModel):
    """Response model for a jurisdiction conflict."""

    regulation: str
    jurisdiction_1: str
    jurisdiction_2: str
    conflict_type: str
    description: str
    severity: str = Field(..., pattern="^(low|medium|high)$")


class ConsensusMetrics(BaseModel):
    """Response model for consensus metrics."""

    reached: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    agreeing_agents: list[str]
    diverging_agents: list[str]
    total_agents: int


class FullQueryResponse(BaseModel):
    """Complete response model for valid query."""

    query: str
    intent: str
    answer: str
    citations: list[CitationResponse]
    decay_scores: list[DecayScoreResponse]
    conflicts: list[ConflictResponse]
    consensus: ConsensusMetrics
    roadmap: Optional[dict[str, Any]] = None
    breakdown: Optional[dict[str, Any]] = None
    applicability: Optional[dict[str, Any]] = None
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ErrorResponse(BaseModel):
    """Standardized error response."""

    error: str = Field(..., description="Error message")
    error_type: str = Field(
        ..., description="Type of error (validation, not_found, internal, etc.)"
    )
    details: Optional[dict[str, Any]] = Field(
        default=None, description="Additional error details"
    )
    request_id: Optional[str] = Field(
        default=None, description="Request ID for tracking"
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., pattern="^(ok|degraded|error)$")
    app_name: str
    version: str
    timestamp: str
    components: dict[str, str] = Field(
        default_factory=dict, description="Status of individual components"
    )
