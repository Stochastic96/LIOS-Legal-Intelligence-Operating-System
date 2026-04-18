"""Pydantic models for input validation and request/response handling."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict, model_validator


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


# ---------------------------------------------------------------------------
# Carbon Accounting models
# ---------------------------------------------------------------------------

class Scope1InputModel(BaseModel):
    """Scope 1 direct emission inputs."""
    natural_gas_mwh: float = Field(default=0.0, ge=0, description="Natural gas consumed (MWh)")
    diesel_litres: float = Field(default=0.0, ge=0, description="Diesel consumed (litres)")
    petrol_litres: float = Field(default=0.0, ge=0, description="Petrol consumed (litres)")
    coal_tonnes: float = Field(default=0.0, ge=0, description="Coal consumed (tonnes)")
    fuel_oil_litres: float = Field(default=0.0, ge=0, description="Fuel oil consumed (litres)")
    lpg_litres: float = Field(default=0.0, ge=0, description="LPG consumed (litres)")
    process_emissions_tco2e: float = Field(default=0.0, ge=0, description="Direct process emissions (tCO2e)")
    notes: str = Field(default="", max_length=500)


class Scope2InputModel(BaseModel):
    """Scope 2 purchased energy inputs."""
    electricity_mwh: float = Field(default=0.0, ge=0, description="Purchased electricity (MWh)")
    district_heat_mwh: float = Field(default=0.0, ge=0, description="District heat purchased (MWh)")
    steam_mwh: float = Field(default=0.0, ge=0, description="Steam purchased (MWh)")
    country: str = Field(default="EU", max_length=50, description="Country for grid emission factor")
    use_market_based: bool = Field(default=False, description="Also calculate market-based Scope 2")
    market_based_factor: Optional[float] = Field(
        default=None, ge=0, description="Market-based emission factor (tCO2e/MWh)"
    )
    notes: str = Field(default="", max_length=500)


class Scope3InputModel(BaseModel):
    """Scope 3 value chain emission inputs."""
    # Cat 1 – Purchased goods
    steel_tonnes: float = Field(default=0.0, ge=0)
    aluminium_tonnes: float = Field(default=0.0, ge=0)
    concrete_tonnes: float = Field(default=0.0, ge=0)
    plastics_tonnes: float = Field(default=0.0, ge=0)
    paper_tonnes: float = Field(default=0.0, ge=0)
    chemicals_tonnes: float = Field(default=0.0, ge=0)
    other_purchased_goods_tco2e: float = Field(default=0.0, ge=0)
    # Cat 4 – Transport
    road_freight_tonne_km: float = Field(default=0.0, ge=0)
    sea_freight_tonne_km: float = Field(default=0.0, ge=0)
    air_freight_tonne_km: float = Field(default=0.0, ge=0)
    rail_freight_tonne_km: float = Field(default=0.0, ge=0)
    # Cat 6 – Business travel
    air_travel_km: float = Field(default=0.0, ge=0)
    car_travel_km: float = Field(default=0.0, ge=0)
    rail_travel_km: float = Field(default=0.0, ge=0)
    # Cat 7 – Employee commuting
    employees: int = Field(default=0, ge=0)
    # Cat 12 – End-of-life
    waste_landfill_tonnes: float = Field(default=0.0, ge=0)
    waste_incineration_tonnes: float = Field(default=0.0, ge=0)
    waste_recycling_tonnes: float = Field(default=0.0, ge=0)
    # Other categories (direct tCO2e)
    cat2_capital_goods_tco2e: float = Field(default=0.0, ge=0)
    cat3_fuel_energy_tco2e: float = Field(default=0.0, ge=0)
    cat5_waste_operations_tco2e: float = Field(default=0.0, ge=0)
    cat8_upstream_leased_tco2e: float = Field(default=0.0, ge=0)
    cat9_downstream_transport_tco2e: float = Field(default=0.0, ge=0)
    cat10_processing_sold_products_tco2e: float = Field(default=0.0, ge=0)
    cat11_use_sold_products_tco2e: float = Field(default=0.0, ge=0)
    cat13_downstream_leased_tco2e: float = Field(default=0.0, ge=0)
    cat14_franchises_tco2e: float = Field(default=0.0, ge=0)
    cat15_investments_tco2e: float = Field(default=0.0, ge=0)
    notes: str = Field(default="", max_length=500)


class CarbonCalculationRequest(BaseModel):
    """Request model for carbon emission calculation."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "company_name": "Acme GmbH",
            "reporting_year": 2024,
            "employees": 500,
            "revenue_meur": 120.0,
            "scope1": {"natural_gas_mwh": 1500, "diesel_litres": 20000},
            "scope2": {"electricity_mwh": 3000, "country": "Germany"},
            "scope3": {"employees": 500, "air_travel_km": 200000},
        }
    })

    company_name: str = Field(default="Company", max_length=200)
    reporting_year: int = Field(default=2024, ge=2000, le=2100)
    employees: Optional[int] = Field(default=None, ge=0)
    revenue_meur: Optional[float] = Field(default=None, ge=0)
    scope1: Scope1InputModel = Field(default_factory=Scope1InputModel)
    scope2: Scope2InputModel = Field(default_factory=Scope2InputModel)
    scope3: Scope3InputModel = Field(default_factory=Scope3InputModel)


# ---------------------------------------------------------------------------
# Supply chain models
# ---------------------------------------------------------------------------

class SupplierRegistrationRequest(BaseModel):
    """Request model to register a new supplier."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Textron Components Ltd",
            "country": "Bangladesh",
            "sector": "textile",
            "tier": 1,
            "environmental_score": 45.0,
            "social_score": 35.0,
            "governance_score": 55.0,
            "annual_spend_eur": 500000,
            "employees": 2000,
        }
    })

    name: str = Field(..., min_length=1, max_length=200)
    country: str = Field(..., min_length=1, max_length=100)
    sector: str = Field(..., min_length=1, max_length=100)
    tier: int = Field(default=1, ge=1, le=5, description="Supply chain tier (1=direct)")
    environmental_score: float = Field(default=50.0, ge=0, le=100)
    social_score: float = Field(default=50.0, ge=0, le=100)
    governance_score: float = Field(default=50.0, ge=0, le=100)
    data_quality: float = Field(default=50.0, ge=0, le=100)
    annual_spend_eur: float = Field(default=0.0, ge=0)
    employees: int = Field(default=0, ge=0)
    contact_email: str = Field(default="", max_length=200)
    website: str = Field(default="", max_length=300)
    certifications: list[str] = Field(default_factory=list)
    notes: str = Field(default="", max_length=1000)


# ---------------------------------------------------------------------------
# Double Materiality models
# ---------------------------------------------------------------------------

class TopicAssessmentInput(BaseModel):
    """Input for a single ESRS topic in the double materiality assessment."""
    esrs_code: str = Field(..., min_length=2, max_length=10, description="ESRS topic code (e.g. 'E1', 'S1')")
    sub_topic: str = Field(default="", max_length=200)
    impact_severity: float = Field(default=2.0, ge=1.0, le=5.0, description="Severity of impact (1-5)")
    impact_scale: float = Field(default=2.0, ge=1.0, le=5.0, description="Scale/breadth of impact (1-5)")
    impact_likelihood: float = Field(default=2.0, ge=1.0, le=5.0, description="Likelihood of impact (1-5)")
    financial_likelihood: float = Field(default=2.0, ge=1.0, le=5.0, description="Likelihood of financial effect (1-5)")
    financial_magnitude: float = Field(default=2.0, ge=1.0, le=5.0, description="Magnitude of financial effect (1-5)")
    financial_time_horizon: str = Field(default="medium", description="Time horizon: short/medium/long")

    @field_validator("financial_time_horizon")
    @classmethod
    def validate_time_horizon(cls, v: str) -> str:
        allowed = {"short", "medium", "long"}
        if v.lower() not in allowed:
            raise ValueError(f"time_horizon must be one of {allowed}")
        return v.lower()

    @field_validator("esrs_code")
    @classmethod
    def validate_esrs_code(cls, v: str) -> str:
        return v.upper().strip()


class MaterialityAssessmentRequest(BaseModel):
    """Request model for double materiality assessment."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "company_profile": {
                "name": "Acme Manufacturing GmbH",
                "employees": 750,
                "sector": "manufacturing",
            },
            "topics": [
                {
                    "esrs_code": "E1",
                    "sub_topic": "GHG emissions",
                    "impact_severity": 4,
                    "impact_scale": 3,
                    "impact_likelihood": 4,
                    "financial_likelihood": 4,
                    "financial_magnitude": 4,
                    "financial_time_horizon": "short",
                }
            ],
        }
    })

    company_profile: dict[str, Any] = Field(..., description="Company profile data")
    topics: list[TopicAssessmentInput] = Field(
        ..., min_length=1, description="List of ESRS topics to assess"
    )
