"""Supply Chain Due Diligence module – CSRD Art. 8 & CSDDD aligned."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SupplierESGScore:
    """ESG scores (0–100) for a supplier, higher = better performance."""
    environmental: float  # E.g. emissions, waste, water
    social: float         # E.g. labour rights, health & safety
    governance: float     # E.g. anti-corruption, board diversity
    data_quality: float   # Confidence in the data (0=estimated, 100=verified)

    @property
    def composite(self) -> float:
        """Weighted composite ESG score."""
        return round(
            0.40 * self.environmental + 0.35 * self.social + 0.25 * self.governance, 1
        )


@dataclass
class Supplier:
    """Supplier entity with full ESG profile."""
    supplier_id: str
    name: str
    country: str
    sector: str
    tier: int  # 1 = direct, 2 = tier-2, etc.
    esg_scores: SupplierESGScore
    annual_spend_eur: float = 0.0
    employees: int = 0
    contact_email: str = ""
    website: str = ""
    certifications: list[str] = field(default_factory=list)  # ISO 14001, SA8000, etc.
    audit_status: AuditStatus = AuditStatus.NOT_STARTED
    last_audit_date: str | None = None
    next_audit_date: str | None = None
    corrective_actions: list[str] = field(default_factory=list)
    notes: str = ""
    created_at: str = field(default_factory=lambda: date.today().isoformat())
    updated_at: str = field(default_factory=lambda: date.today().isoformat())


@dataclass
class RiskFactor:
    """Individual risk factor contributing to overall supplier risk."""
    name: str
    weight: float        # Contribution weight (0.0–1.0, total must sum to 1.0)
    score: float         # Raw score (0=best, 10=worst)
    weighted_score: float
    description: str


@dataclass
class SupplierRiskAssessment:
    """Comprehensive risk assessment for a supplier."""
    supplier_id: str
    supplier_name: str
    overall_risk: RiskLevel
    overall_score: float  # 0–100, higher = more risk
    risk_factors: list[RiskFactor]
    csrd_compliance_gaps: list[str]
    recommended_actions: list[str]
    assessment_date: str
    due_diligence_complete: bool
    csrd_article_references: list[str]


@dataclass
class PortfolioRiskSummary:
    """Summary of risk across all suppliers in a portfolio."""
    total_suppliers: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    average_esg_score: float
    total_annual_spend_eur: float
    high_risk_spend_eur: float
    coverage_percent: float       # % of suppliers assessed
    top_risks: list[str]
    csrd_compliance_status: str


# ---------------------------------------------------------------------------
# CSRD Due Diligence Checklist Items
# ---------------------------------------------------------------------------

CSRD_DUE_DILIGENCE_CHECKLIST: list[dict[str, str]] = [
    {
        "id": "DD-E-01",
        "category": "Environmental",
        "requirement": "GHG emissions data collected from supplier (Scope 1 & 2 minimum)",
        "csrd_reference": "ESRS E1, CSRD Art.8",
        "csddd_reference": "CSDDD Art.7",
    },
    {
        "id": "DD-E-02",
        "category": "Environmental",
        "requirement": "Supplier has or is working towards a science-based GHG target",
        "csrd_reference": "ESRS E1-4",
        "csddd_reference": "CSDDD Art.15",
    },
    {
        "id": "DD-E-03",
        "category": "Environmental",
        "requirement": "Water usage and wastewater treatment data available",
        "csrd_reference": "ESRS E3",
        "csddd_reference": "CSDDD Art.7",
    },
    {
        "id": "DD-E-04",
        "category": "Environmental",
        "requirement": "No involvement in deforestation or biodiversity-harmful activities",
        "csrd_reference": "ESRS E4",
        "csddd_reference": "CSDDD Art.7",
    },
    {
        "id": "DD-S-01",
        "category": "Social",
        "requirement": "Living wage policy in place for direct workers",
        "csrd_reference": "ESRS S1",
        "csddd_reference": "CSDDD Art.7",
    },
    {
        "id": "DD-S-02",
        "category": "Social",
        "requirement": "No forced or child labour (ILO Conventions 29, 105, 138, 182)",
        "csrd_reference": "ESRS S2",
        "csddd_reference": "CSDDD Art.3",
    },
    {
        "id": "DD-S-03",
        "category": "Social",
        "requirement": "Freedom of association and collective bargaining respected",
        "csrd_reference": "ESRS S1",
        "csddd_reference": "CSDDD Art.3",
    },
    {
        "id": "DD-S-04",
        "category": "Social",
        "requirement": "Health & safety management system in place (ISO 45001 or equivalent)",
        "csrd_reference": "ESRS S1",
        "csddd_reference": "CSDDD Art.7",
    },
    {
        "id": "DD-G-01",
        "category": "Governance",
        "requirement": "Anti-bribery and anti-corruption policy in place",
        "csrd_reference": "ESRS G1",
        "csddd_reference": "CSDDD Art.7",
    },
    {
        "id": "DD-G-02",
        "category": "Governance",
        "requirement": "Supplier code of conduct signed",
        "csrd_reference": "CSRD Art.8",
        "csddd_reference": "CSDDD Art.5",
    },
    {
        "id": "DD-G-03",
        "category": "Governance",
        "requirement": "Grievance mechanism accessible to workers and communities",
        "csrd_reference": "ESRS S2, S3",
        "csddd_reference": "CSDDD Art.9",
    },
    {
        "id": "DD-G-04",
        "category": "Governance",
        "requirement": "Remediation plan in place for any identified adverse impacts",
        "csrd_reference": "CSRD Art.8",
        "csddd_reference": "CSDDD Art.11",
    },
]

# Country risk indices (0–10, lower = better governance/lower risk)
# Source: Transparency International CPI, World Bank Governance Indicators
COUNTRY_RISK_INDEX: dict[str, float] = {
    "denmark": 1.0, "finland": 1.0, "norway": 1.0, "sweden": 1.1, "netherlands": 1.2,
    "germany": 1.5, "austria": 1.5, "luxembourg": 1.4, "france": 2.0, "uk": 2.0,
    "spain": 2.5, "portugal": 2.3, "italy": 3.0, "poland": 2.8, "czechia": 2.5,
    "romania": 4.0, "bulgaria": 4.5, "hungary": 4.0, "greece": 3.5,
    "turkey": 5.5, "ukraine": 5.5, "russia": 8.0,
    "china": 6.0, "india": 5.5, "vietnam": 5.5, "bangladesh": 7.0,
    "indonesia": 5.5, "philippines": 5.5, "thailand": 5.0, "malaysia": 4.5,
    "brazil": 5.5, "mexico": 6.0, "argentina": 5.5, "colombia": 6.0,
    "nigeria": 7.5, "ghana": 5.0, "kenya": 6.0, "ethiopia": 7.0,
    "south africa": 5.5, "egypt": 6.5,
    "usa": 2.5, "canada": 1.5, "australia": 1.5, "japan": 1.5,
    "south korea": 2.5, "singapore": 1.0,
}

# Sector risk multipliers (for social/environmental risk)
SECTOR_RISK_MULTIPLIER: dict[str, float] = {
    "agriculture": 1.8, "fishing": 1.7, "mining": 1.9, "oil and gas": 2.0,
    "textile": 1.8, "garment": 1.9, "leather": 1.8, "footwear": 1.8,
    "electronics": 1.5, "construction": 1.6, "chemicals": 1.7,
    "food processing": 1.5, "transport": 1.3, "logistics": 1.2,
    "retail": 1.1, "finance": 1.0, "software": 0.8, "services": 0.9,
    "manufacturing": 1.4, "automotive": 1.4,
}


class SupplyChainDueDiligenceEngine:
    """CSRD Art. 8 and CSDDD-aligned supply chain due diligence engine.

    Manages supplier registration, ESG scoring, risk assessment,
    and compliance documentation.
    """

    def __init__(self) -> None:
        self._suppliers: dict[str, Supplier] = {}

    # ------------------------------------------------------------------
    # Supplier management
    # ------------------------------------------------------------------

    def add_supplier(
        self,
        name: str,
        country: str,
        sector: str,
        tier: int = 1,
        environmental_score: float = 50.0,
        social_score: float = 50.0,
        governance_score: float = 50.0,
        data_quality: float = 50.0,
        annual_spend_eur: float = 0.0,
        employees: int = 0,
        contact_email: str = "",
        website: str = "",
        certifications: list[str] | None = None,
        notes: str = "",
    ) -> Supplier:
        """Register a new supplier and return the created entity."""
        supplier_id = str(uuid.uuid4())
        esg = SupplierESGScore(
            environmental=min(100.0, max(0.0, environmental_score)),
            social=min(100.0, max(0.0, social_score)),
            governance=min(100.0, max(0.0, governance_score)),
            data_quality=min(100.0, max(0.0, data_quality)),
        )
        supplier = Supplier(
            supplier_id=supplier_id,
            name=name,
            country=country,
            sector=sector,
            tier=tier,
            esg_scores=esg,
            annual_spend_eur=annual_spend_eur,
            employees=employees,
            contact_email=contact_email,
            website=website,
            certifications=certifications or [],
            notes=notes,
        )
        self._suppliers[supplier_id] = supplier
        return supplier

    def get_supplier(self, supplier_id: str) -> Supplier | None:
        return self._suppliers.get(supplier_id)

    def list_suppliers(self) -> list[Supplier]:
        return list(self._suppliers.values())

    def update_supplier_esg(
        self,
        supplier_id: str,
        environmental: float | None = None,
        social: float | None = None,
        governance: float | None = None,
        data_quality: float | None = None,
    ) -> Supplier | None:
        """Update ESG scores for an existing supplier."""
        supplier = self._suppliers.get(supplier_id)
        if supplier is None:
            return None
        if environmental is not None:
            supplier.esg_scores.environmental = min(100.0, max(0.0, environmental))
        if social is not None:
            supplier.esg_scores.social = min(100.0, max(0.0, social))
        if governance is not None:
            supplier.esg_scores.governance = min(100.0, max(0.0, governance))
        if data_quality is not None:
            supplier.esg_scores.data_quality = min(100.0, max(0.0, data_quality))
        supplier.updated_at = date.today().isoformat()
        return supplier

    # ------------------------------------------------------------------
    # Risk assessment
    # ------------------------------------------------------------------

    def assess_risk(self, supplier_id: str) -> SupplierRiskAssessment | None:
        """Run full risk assessment for a supplier.

        Risk model:
        - ESG score gap (inverse of composite ESG → risk)
        - Country risk (Transparency International / World Bank proxy)
        - Sector risk (sector-specific multiplier)
        - Data quality penalty (low quality inflates uncertainty)
        - Tier penalty (higher tier = less visibility)
        """
        supplier = self._suppliers.get(supplier_id)
        if supplier is None:
            return None

        # Factor 1: ESG performance risk (inverse of composite, 0–10)
        esg_gap = (100.0 - supplier.esg_scores.composite) / 10.0  # 0=best, 10=worst
        esg_weight = 0.35
        esg_rf = RiskFactor(
            name="ESG Performance",
            weight=esg_weight,
            score=round(esg_gap, 1),
            weighted_score=round(esg_gap * esg_weight, 2),
            description=f"Composite ESG score: {supplier.esg_scores.composite}/100",
        )

        # Factor 2: Country risk
        country_key = supplier.country.lower()
        country_score = COUNTRY_RISK_INDEX.get(country_key, 5.0)
        country_weight = 0.25
        country_rf = RiskFactor(
            name="Country Risk",
            weight=country_weight,
            score=round(country_score, 1),
            weighted_score=round(country_score * country_weight, 2),
            description=f"Country governance/political risk index for {supplier.country}",
        )

        # Factor 3: Sector risk
        sector_key = supplier.sector.lower()
        sector_mult = SECTOR_RISK_MULTIPLIER.get(sector_key, 1.3)
        sector_base = 4.0  # Base sector risk score
        sector_score = min(10.0, sector_base * sector_mult)
        sector_weight = 0.20
        sector_rf = RiskFactor(
            name="Sector Risk",
            weight=sector_weight,
            score=round(sector_score, 1),
            weighted_score=round(sector_score * sector_weight, 2),
            description=f"Sector '{supplier.sector}' risk profile (multiplier: {sector_mult})",
        )

        # Factor 4: Data quality penalty
        data_gap = (100.0 - supplier.esg_scores.data_quality) / 10.0
        data_weight = 0.10
        data_rf = RiskFactor(
            name="Data Quality",
            weight=data_weight,
            score=round(data_gap, 1),
            weighted_score=round(data_gap * data_weight, 2),
            description=f"Data quality score: {supplier.esg_scores.data_quality}/100 – "
                        "low quality increases uncertainty",
        )

        # Factor 5: Tier visibility
        tier_score = min(10.0, (supplier.tier - 1) * 2.5)
        tier_weight = 0.10
        tier_rf = RiskFactor(
            name="Supply Chain Tier",
            weight=tier_weight,
            score=round(tier_score, 1),
            weighted_score=round(tier_score * tier_weight, 2),
            description=f"Tier {supplier.tier} supplier – deeper tiers have less visibility",
        )

        risk_factors = [esg_rf, country_rf, sector_rf, data_rf, tier_rf]

        # Overall risk score (0–10 weighted sum → convert to 0–100)
        weighted_sum = sum(rf.weighted_score for rf in risk_factors)
        overall_score = round(weighted_sum * 10.0, 1)  # scale to 0–100

        # Risk level
        if overall_score >= 70:
            level = RiskLevel.CRITICAL
        elif overall_score >= 50:
            level = RiskLevel.HIGH
        elif overall_score >= 30:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW

        # CSRD compliance gaps
        gaps = self._identify_compliance_gaps(supplier)

        # Recommended actions
        actions = self._recommend_actions(supplier, level, gaps)

        return SupplierRiskAssessment(
            supplier_id=supplier_id,
            supplier_name=supplier.name,
            overall_risk=level,
            overall_score=overall_score,
            risk_factors=risk_factors,
            csrd_compliance_gaps=gaps,
            recommended_actions=actions,
            assessment_date=date.today().isoformat(),
            due_diligence_complete=len(gaps) == 0,
            csrd_article_references=[
                "CSRD Art.8 – Value chain due diligence",
                "ESRS S2 – Workers in the value chain",
                "ESRS E1 – Climate change (Scope 3)",
            ],
        )

    def assess_all_risks(self) -> list[SupplierRiskAssessment]:
        """Assess risk for all registered suppliers."""
        results = []
        for supplier_id in self._suppliers:
            assessment = self.assess_risk(supplier_id)
            if assessment:
                results.append(assessment)
        return results

    def get_portfolio_summary(self) -> PortfolioRiskSummary:
        """Aggregate risk summary across all suppliers."""
        assessments = self.assess_all_risks()
        suppliers = self.list_suppliers()

        counts = {r: 0 for r in RiskLevel}
        for a in assessments:
            counts[a.overall_risk] += 1

        total_spend = sum(s.annual_spend_eur for s in suppliers)
        high_risk_spend = sum(
            s.annual_spend_eur
            for s, a in zip(suppliers, assessments)
            if a.overall_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        )

        esg_scores = [s.esg_scores.composite for s in suppliers]
        avg_esg = round(sum(esg_scores) / len(esg_scores), 1) if esg_scores else 0.0

        coverage = (
            len([a for a in assessments if a.due_diligence_complete]) / len(assessments) * 100
            if assessments else 0.0
        )

        top_risks = self._identify_top_portfolio_risks(assessments)

        csrd_status = "Compliant" if coverage >= 80 else (
            "In Progress" if coverage >= 40 else "Non-Compliant"
        )

        return PortfolioRiskSummary(
            total_suppliers=len(suppliers),
            critical_count=counts[RiskLevel.CRITICAL],
            high_count=counts[RiskLevel.HIGH],
            medium_count=counts[RiskLevel.MEDIUM],
            low_count=counts[RiskLevel.LOW],
            average_esg_score=avg_esg,
            total_annual_spend_eur=total_spend,
            high_risk_spend_eur=high_risk_spend,
            coverage_percent=round(coverage, 1),
            top_risks=top_risks,
            csrd_compliance_status=csrd_status,
        )

    def get_checklist(self) -> list[dict[str, str]]:
        """Return the CSRD due diligence checklist."""
        return CSRD_DUE_DILIGENCE_CHECKLIST

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _identify_compliance_gaps(self, supplier: Supplier) -> list[str]:
        gaps: list[str] = []
        if supplier.esg_scores.environmental < 40:
            gaps.append("Environmental score below threshold – GHG data and environmental policy required")
        if supplier.esg_scores.social < 40:
            gaps.append("Social score below threshold – Labour rights due diligence required (CSDDD Art.7)")
        if supplier.esg_scores.governance < 40:
            gaps.append("Governance score below threshold – Anti-corruption policy and code of conduct required")
        if not supplier.certifications:
            gaps.append("No sustainability certifications – Consider ISO 14001, SA8000, or equivalent")
        if supplier.audit_status == AuditStatus.NOT_STARTED:
            gaps.append("No audit conducted – Initial on-site or desk audit required (CSRD Art.8)")
        if supplier.esg_scores.data_quality < 50:
            gaps.append("Low data quality – Supplier self-assessment or third-party verification required")
        return gaps

    def _recommend_actions(
        self,
        supplier: Supplier,
        risk_level: RiskLevel,
        gaps: list[str],
    ) -> list[str]:
        actions: list[str] = []
        if risk_level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
            actions.append(f"Escalate {supplier.name} to procurement risk committee immediately")
            actions.append("Conduct on-site audit within 90 days")
            actions.append("Request corrective action plan within 30 days")
        elif risk_level == RiskLevel.MEDIUM:
            actions.append("Schedule supplier ESG review call within 60 days")
            actions.append("Request signed supplier code of conduct")
        else:
            actions.append("Continue annual monitoring cadence")

        if not supplier.certifications:
            actions.append("Encourage supplier to obtain ISO 14001 environmental certification")
        if supplier.esg_scores.data_quality < 60:
            actions.append("Request third-party verified ESG data or complete supplier self-assessment")
        if supplier.tier > 1:
            actions.append(f"Map tier-{supplier.tier} supplier's own supply chain for further visibility")

        return actions

    def _identify_top_portfolio_risks(
        self, assessments: list[SupplierRiskAssessment]
    ) -> list[str]:
        if not assessments:
            return []
        critical = [a.supplier_name for a in assessments if a.overall_risk == RiskLevel.CRITICAL]
        if critical:
            return [f"Critical risk suppliers: {', '.join(critical[:3])}"]
        high = [a.supplier_name for a in assessments if a.overall_risk == RiskLevel.HIGH]
        if high:
            return [f"High-risk suppliers requiring action: {', '.join(high[:5])}"]
        return ["No critical or high-risk suppliers identified"]
