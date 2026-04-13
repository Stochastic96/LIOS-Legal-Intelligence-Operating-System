"""
Feature 5 – Compliance Roadmap Generator.

Produces a personalised, time-ordered compliance action plan
based on the regulations that apply to a given company.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from lios.agents.features.applicability_checker import (
    ApplicabilityChecker,
    ApplicabilityResult,
    CompanyProfile,
    RegulationType,
)


@dataclass
class RoadmapStep:
    step_number: int
    regulation: str
    action: str
    deadline: Optional[date]
    priority: str          # "HIGH" | "MEDIUM" | "LOW"
    details: str = ""


@dataclass
class ComplianceRoadmap:
    company_name: str
    generated_on: date
    steps: list[RoadmapStep] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "company_name": self.company_name,
            "generated_on": str(self.generated_on),
            "steps": [
                {
                    "step": s.step_number,
                    "regulation": s.regulation,
                    "action": s.action,
                    "deadline": str(s.deadline) if s.deadline else None,
                    "priority": s.priority,
                    "details": s.details,
                }
                for s in self.steps
            ],
        }


# ── Action templates per regulation ──────────────────────────────────────────
_ACTIONS: dict[str, list[dict]] = {
    "CSRD": [
        {
            "action": "Gap analysis against ESRS standards",
            "priority": "HIGH",
            "details": "Assess current non-financial disclosures vs. ESRS E1–S4 requirements.",
        },
        {
            "action": "Appoint sustainability reporting function",
            "priority": "HIGH",
            "details": "Designate team responsible for double materiality assessment.",
        },
        {
            "action": "Double materiality assessment",
            "priority": "HIGH",
            "details": "Identify material sustainability impacts, risks and opportunities (ESRS 1 §18).",
        },
        {
            "action": "Implement data collection processes",
            "priority": "MEDIUM",
            "details": "Set up internal controls for ESG data aligned with ESRS disclosures.",
        },
        {
            "action": "Engage auditor for limited assurance",
            "priority": "MEDIUM",
            "details": "CSRD Art. 26a requires limited assurance from a statutory auditor.",
        },
    ],
    "SFDR": [
        {
            "action": "Classify financial products (Art. 6 / 8 / 9)",
            "priority": "HIGH",
            "details": "Determine ESG classification for each product; update prospectuses.",
        },
        {
            "action": "Publish entity-level PAI statement",
            "priority": "HIGH",
            "details": "Principal Adverse Impacts statement on website (Art. 4 SFDR).",
        },
    ],
    "EU_TAXONOMY": [
        {
            "action": "Screen activities against Taxonomy criteria",
            "priority": "HIGH",
            "details": "Identify eligible and aligned revenue, capex, opex (Art. 8 disclosures).",
        },
    ],
    "CSDDD": [
        {
            "action": "Map value chain for human rights & environment risks",
            "priority": "HIGH",
            "details": "CSDDD Art. 5 – identify adverse impacts across own operations and supply chain.",
        },
        {
            "action": "Establish grievance mechanism",
            "priority": "MEDIUM",
            "details": "CSDDD Art. 9 – accessible complaints procedure for affected persons.",
        },
    ],
}


class RoadmapGenerator:
    """Generate a compliance roadmap for a given company profile."""

    def __init__(self) -> None:
        self._checker = ApplicabilityChecker()

    def generate(self, profile: CompanyProfile) -> ComplianceRoadmap:
        results = self._checker.check_all(profile)
        applicable = [r for r in results if r.applies]

        steps: list[RoadmapStep] = []
        step_num = 1

        for result in applicable:
            reg = result.regulation
            phase_date = (
                date(result.phase_in_year - 1, 12, 31)  # year-end before first report
                if result.phase_in_year
                else None
            )
            for action_template in _ACTIONS.get(reg, []):
                steps.append(
                    RoadmapStep(
                        step_number=step_num,
                        regulation=reg,
                        action=action_template["action"],
                        deadline=phase_date,
                        priority=action_template["priority"],
                        details=action_template["details"],
                    )
                )
                step_num += 1

        # Sort: HIGH priority first, then by deadline
        steps.sort(
            key=lambda s: ({"HIGH": 0, "MEDIUM": 1, "LOW": 2}[s.priority], s.deadline or date.max)
        )
        for i, step in enumerate(steps, start=1):
            step.step_number = i

        return ComplianceRoadmap(
            company_name=profile.name,
            generated_on=date.today(),
            steps=steps,
        )
