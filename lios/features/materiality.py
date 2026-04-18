"""Double Materiality Assessment module – CSRD Art. 4 / ESRS 1 aligned."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MaterialityDimension(str, Enum):
    IMPACT = "impact"       # Inside-out: company's effect on environment/society
    FINANCIAL = "financial"  # Outside-in: ESG risks/opportunities affecting the company


class MaterialityLevel(str, Enum):
    NOT_MATERIAL = "not_material"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


# ESRS topic taxonomy (ESRS 1, Appendix A)
ESRS_TOPICS: dict[str, dict[str, Any]] = {
    "E1": {
        "standard": "ESRS E1",
        "topic": "Climate Change",
        "sub_topics": ["GHG emissions", "Climate adaptation", "Energy"],
        "iiro_categories": ["Mitigation", "Adaptation", "Physical risk", "Transition risk"],
    },
    "E2": {
        "standard": "ESRS E2",
        "topic": "Pollution",
        "sub_topics": ["Air pollution", "Water pollution", "Soil pollution", "Hazardous substances"],
        "iiro_categories": ["Emissions to air", "Emissions to water", "Emissions to soil"],
    },
    "E3": {
        "standard": "ESRS E3",
        "topic": "Water & Marine Resources",
        "sub_topics": ["Water consumption", "Water withdrawal", "Marine resources"],
        "iiro_categories": ["Water scarcity", "Water quality", "Marine ecosystem"],
    },
    "E4": {
        "standard": "ESRS E4",
        "topic": "Biodiversity & Ecosystems",
        "sub_topics": ["Land use change", "Ecosystem degradation", "Species loss"],
        "iiro_categories": ["Direct drivers", "Indirect drivers"],
    },
    "E5": {
        "standard": "ESRS E5",
        "topic": "Resource Use & Circular Economy",
        "sub_topics": ["Resource inflows", "Resource outflows", "Waste"],
        "iiro_categories": ["Resource efficiency", "Waste management"],
    },
    "S1": {
        "standard": "ESRS S1",
        "topic": "Own Workforce",
        "sub_topics": ["Working conditions", "Equal treatment", "Labour rights", "Safety"],
        "iiro_categories": ["Working hours", "Remuneration", "H&S", "Discrimination"],
    },
    "S2": {
        "standard": "ESRS S2",
        "topic": "Workers in the Value Chain",
        "sub_topics": ["Supply chain labour", "Subcontracted workers"],
        "iiro_categories": ["Forced labour", "Child labour", "Fair wages"],
    },
    "S3": {
        "standard": "ESRS S3",
        "topic": "Affected Communities",
        "sub_topics": ["Local communities", "Indigenous peoples", "Economic impacts"],
        "iiro_categories": ["Community impacts", "Human rights"],
    },
    "S4": {
        "standard": "ESRS S4",
        "topic": "Consumers & End-users",
        "sub_topics": ["Product safety", "Privacy", "Responsible marketing"],
        "iiro_categories": ["Product harm", "Data protection", "Consumer rights"],
    },
    "G1": {
        "standard": "ESRS G1",
        "topic": "Business Conduct",
        "sub_topics": ["Corporate culture", "Whistleblowing", "Anti-corruption", "Lobbying"],
        "iiro_categories": ["Bribery", "Conflicts of interest", "Political engagement"],
    },
}


@dataclass
class MaterialityTopic:
    """A single sustainability topic assessed for double materiality."""
    esrs_code: str            # E.g. "E1", "S1"
    topic_name: str
    sub_topic: str

    # Impact materiality (inside-out)
    impact_score: float       # 1–5 scale
    impact_scale: float       # Breadth: how many affected (1=few, 5=widespread)
    impact_severity: float    # How serious (1=minor, 5=severe/irreversible)
    impact_likelihood: float  # Probability of impact (1=unlikely, 5=certain)
    impact_material: bool = False

    # Financial materiality (outside-in)
    financial_score: float = 0.0   # 1–5 scale
    financial_likelihood: float = 0.0
    financial_magnitude: float = 0.0
    financial_time_horizon: str = "medium"  # "short", "medium", "long"
    financial_material: bool = False

    # Double materiality outcome
    double_material: bool = False
    materiality_level: MaterialityLevel = MaterialityLevel.NOT_MATERIAL
    rationale: str = ""
    priority_actions: list[str] = field(default_factory=list)


@dataclass
class MaterialityMatrix:
    """Double materiality matrix output."""
    company_profile: dict[str, Any]
    assessed_topics: list[MaterialityTopic]
    material_topics: list[str]
    mandatory_topics: list[str]   # ESRS 1 & 2 are always mandatory
    recommended_disclosures: list[str]
    assessment_summary: str
    next_steps: list[str]
    csrd_article_references: list[str] = field(default_factory=list)


class DoubleMaterialityEngine:
    """CSRD Art. 4 / ESRS 1 compliant Double Materiality Assessment engine.

    Implements the two-dimensional assessment:
    1. Impact materiality (IRO - Impacts, Risks, Opportunities from inside-out)
    2. Financial materiality (outside-in: how ESG topics affect the company)

    A topic is material if it exceeds the threshold on EITHER dimension.
    """

    # Threshold for materiality (on 1–5 scale)
    IMPACT_THRESHOLD = 2.5
    FINANCIAL_THRESHOLD = 2.5

    def assess(
        self,
        company_profile: dict[str, Any],
        topic_inputs: list[dict[str, Any]],
    ) -> MaterialityMatrix:
        """Run double materiality assessment.

        Args:
            company_profile: Company profile dict.
            topic_inputs: List of topic assessment dicts. Each must have:
                - esrs_code (e.g. "E1")
                - sub_topic (str)
                - impact_severity (1–5)
                - impact_scale (1–5)
                - impact_likelihood (1–5)
                - financial_likelihood (1–5)
                - financial_magnitude (1–5)
                - financial_time_horizon ("short"/"medium"/"long")

        Returns:
            MaterialityMatrix with all assessed topics.
        """
        assessed: list[MaterialityTopic] = []

        for inp in topic_inputs:
            code = inp.get("esrs_code", "")
            esrs_meta = ESRS_TOPICS.get(code, {})
            topic_name = esrs_meta.get("topic", code)

            severity = float(inp.get("impact_severity", 1))
            scale = float(inp.get("impact_scale", 1))
            i_likelihood = float(inp.get("impact_likelihood", 1))
            f_likelihood = float(inp.get("financial_likelihood", 1))
            f_magnitude = float(inp.get("financial_magnitude", 1))
            time_horizon = inp.get("financial_time_horizon", "medium")

            # Clamp 1–5
            severity = max(1.0, min(5.0, severity))
            scale = max(1.0, min(5.0, scale))
            i_likelihood = max(1.0, min(5.0, i_likelihood))
            f_likelihood = max(1.0, min(5.0, f_likelihood))
            f_magnitude = max(1.0, min(5.0, f_magnitude))

            # Impact score: weighted combination (GRI / ESRS 1 methodology)
            impact_score = (0.40 * severity + 0.30 * scale + 0.30 * i_likelihood)
            impact_material = impact_score >= self.IMPACT_THRESHOLD

            # Financial score: likelihood × magnitude (TCFD / ESRS 1)
            financial_score = (0.50 * f_likelihood + 0.50 * f_magnitude)
            # Time horizon adjustment
            time_discount = {"short": 1.0, "medium": 0.85, "long": 0.70}.get(time_horizon, 0.85)
            financial_score *= time_discount
            financial_material = financial_score >= self.FINANCIAL_THRESHOLD

            double_material = impact_material or financial_material

            # Materiality level
            combined = max(impact_score, financial_score)
            if combined >= 4.5:
                level = MaterialityLevel.VERY_HIGH
            elif combined >= 3.5:
                level = MaterialityLevel.HIGH
            elif combined >= 2.5:
                level = MaterialityLevel.MEDIUM
            elif combined >= 1.5:
                level = MaterialityLevel.LOW
            else:
                level = MaterialityLevel.NOT_MATERIAL

            if not double_material:
                level = MaterialityLevel.NOT_MATERIAL

            rationale = self._build_rationale(
                topic_name, impact_score, financial_score,
                impact_material, financial_material, time_horizon
            )
            actions = self._priority_actions(code, level, impact_material, financial_material)

            assessed.append(MaterialityTopic(
                esrs_code=code,
                topic_name=topic_name,
                sub_topic=inp.get("sub_topic", topic_name),
                impact_score=round(impact_score, 2),
                impact_scale=scale,
                impact_severity=severity,
                impact_likelihood=i_likelihood,
                impact_material=impact_material,
                financial_score=round(financial_score, 2),
                financial_likelihood=f_likelihood,
                financial_magnitude=f_magnitude,
                financial_time_horizon=time_horizon,
                financial_material=financial_material,
                double_material=double_material,
                materiality_level=level,
                rationale=rationale,
                priority_actions=actions,
            ))

        material_codes = [t.esrs_code for t in assessed if t.double_material]
        mandatory = ["ESRS 1", "ESRS 2"]  # Always required per CSRD
        disclosures = self._build_disclosure_list(assessed)
        summary = self._build_summary(company_profile, assessed)
        next_steps = self._build_next_steps(assessed, material_codes)

        return MaterialityMatrix(
            company_profile=company_profile,
            assessed_topics=assessed,
            material_topics=material_codes,
            mandatory_topics=mandatory,
            recommended_disclosures=disclosures,
            assessment_summary=summary,
            next_steps=next_steps,
            csrd_article_references=[
                "CSRD Art.4 – Double materiality",
                "ESRS 1 Section 3.4 – IRO materiality assessment",
                "ESRS 2 – General Disclosures (always required)",
            ],
        )

    def get_topic_catalog(self) -> dict[str, dict[str, Any]]:
        """Return the full ESRS topic taxonomy."""
        return ESRS_TOPICS

    def create_default_assessment_inputs(
        self, sector: str = "manufacturing"
    ) -> list[dict[str, Any]]:
        """Return a pre-populated template for common sectors.

        All scores default to 3 (medium) – users should adjust based
        on their actual situation.
        """
        sector_overrides: dict[str, dict[str, dict[str, float]]] = {
            "manufacturing": {
                "E1": {"impact_severity": 4, "impact_scale": 3, "financial_magnitude": 4},
                "E2": {"impact_severity": 3, "impact_scale": 3, "financial_magnitude": 3},
                "S1": {"impact_severity": 3, "impact_scale": 4, "financial_magnitude": 2},
            },
            "finance": {
                "E1": {"impact_severity": 2, "impact_scale": 4, "financial_magnitude": 4},
                "G1": {"impact_severity": 4, "impact_scale": 2, "financial_magnitude": 4},
                "S4": {"impact_severity": 3, "impact_scale": 4, "financial_magnitude": 3},
            },
            "retail": {
                "E1": {"impact_severity": 2, "impact_scale": 3, "financial_magnitude": 3},
                "S2": {"impact_severity": 4, "impact_scale": 4, "financial_magnitude": 3},
                "S4": {"impact_severity": 3, "impact_scale": 4, "financial_magnitude": 3},
            },
        }
        overrides = sector_overrides.get(sector.lower(), {})

        inputs = []
        for code, meta in ESRS_TOPICS.items():
            override = overrides.get(code, {})
            inputs.append({
                "esrs_code": code,
                "sub_topic": meta["topic"],
                "impact_severity": override.get("impact_severity", 2),
                "impact_scale": override.get("impact_scale", 2),
                "impact_likelihood": override.get("impact_likelihood", 2),
                "financial_likelihood": override.get("financial_likelihood", 2),
                "financial_magnitude": override.get("financial_magnitude", 2),
                "financial_time_horizon": "medium",
            })
        return inputs

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_rationale(
        self,
        topic: str,
        impact: float,
        financial: float,
        impact_mat: bool,
        financial_mat: bool,
        time_horizon: str,
    ) -> str:
        parts = []
        if impact_mat:
            parts.append(
                f"Impact material (score {impact:.2f} ≥ {self.IMPACT_THRESHOLD}): "
                f"'{topic}' has significant inside-out impacts on people/environment."
            )
        if financial_mat:
            parts.append(
                f"Financial material (score {financial:.2f} ≥ {self.FINANCIAL_THRESHOLD}, "
                f"time horizon: {time_horizon}): '{topic}' poses material risks/opportunities "
                "to the company's financial position."
            )
        if not parts:
            return f"'{topic}' does not meet materiality thresholds on either dimension."
        return " ".join(parts)

    def _priority_actions(
        self,
        code: str,
        level: MaterialityLevel,
        impact_mat: bool,
        financial_mat: bool,
    ) -> list[str]:
        if level == MaterialityLevel.NOT_MATERIAL:
            return ["Monitor annually; reassess if business model changes."]

        actions = []
        meta = ESRS_TOPICS.get(code, {})
        standard = meta.get("standard", code)

        if level in (MaterialityLevel.VERY_HIGH, MaterialityLevel.HIGH):
            actions.append(f"Include {standard} disclosures in sustainability statement (mandatory).")
            actions.append(f"Set quantitative targets for {meta.get('topic', code)} within 12 months.")
        elif level == MaterialityLevel.MEDIUM:
            actions.append(f"Report on {standard} material IROs with narrative and KPIs.")

        if impact_mat:
            actions.append("Establish stakeholder engagement process for affected groups.")
        if financial_mat:
            actions.append("Integrate into enterprise risk management (ERM) framework.")

        return actions

    def _build_disclosure_list(self, topics: list[MaterialityTopic]) -> list[str]:
        disclosures = ["ESRS 2 – General disclosures (mandatory for all companies)"]
        for t in topics:
            if t.double_material:
                meta = ESRS_TOPICS.get(t.esrs_code, {})
                disclosures.append(
                    f"{meta.get('standard', t.esrs_code)} – {meta.get('topic', t.topic_name)}"
                )
        return disclosures

    def _build_summary(
        self,
        profile: dict[str, Any],
        topics: list[MaterialityTopic],
    ) -> str:
        total = len(topics)
        material = [t for t in topics if t.double_material]
        very_high = [t for t in material if t.materiality_level == MaterialityLevel.VERY_HIGH]
        high = [t for t in material if t.materiality_level == MaterialityLevel.HIGH]

        company = profile.get("name", "The company")
        sector = profile.get("sector", "unspecified sector")

        return (
            f"{company} ({sector}) assessed {total} sustainability topics. "
            f"{len(material)} topics are material under the double materiality principle: "
            f"{len(very_high)} very high, {len(high)} high priority. "
            f"ESRS E1 (Climate Change) and ESRS S1 (Own Workforce) are typically material "
            f"for most sectors. Mandatory ESRS 1 & ESRS 2 disclosures apply regardless of outcome."
        )

    def _build_next_steps(
        self,
        topics: list[MaterialityTopic],
        material_codes: list[str],
    ) -> list[str]:
        steps = [
            "1. Validate DMA findings with board and key stakeholders (ESRS 2 BP-1).",
            "2. Document the DMA methodology and assumptions for auditor review.",
            f"3. Confirm applicability of {len(material_codes)} material ESRS standard(s): "
            f"{', '.join(material_codes) if material_codes else 'None identified'}.",
            "4. Map material IROs to specific ESRS disclosure requirements.",
            "5. Establish data collection for all material KPIs.",
            "6. Set time-bound targets for highest-priority topics.",
            "7. Integrate DMA into strategy and financial planning cycle.",
        ]
        return steps
