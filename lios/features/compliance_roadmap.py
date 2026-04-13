"""Compliance Roadmap Generator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RoadmapStep:
    step_number: int
    title: str
    description: str
    deadline: str
    regulation: str
    priority: str  # "critical" | "high" | "medium" | "low"
    articles_cited: list[str] = field(default_factory=list)


@dataclass
class ComplianceRoadmap:
    company_profile: dict[str, Any]
    applicable_regulations: list[str]
    steps: list[RoadmapStep]
    summary: str


class ComplianceRoadmapGenerator:
    """Generate an ordered compliance roadmap based on company profile."""

    def generate_roadmap(self, company_profile: dict[str, Any]) -> ComplianceRoadmap:
        employees = company_profile.get("employees", 0)
        turnover = company_profile.get("turnover_eur", 0)
        balance_sheet = company_profile.get("balance_sheet_eur", 0)
        listed = company_profile.get("listed", False)
        sector = company_profile.get("sector", "general").lower()
        jurisdiction = company_profile.get("jurisdiction", "EU").lower()
        is_financial = sector in {"finance", "financial services", "asset management", "banking", "insurance"}

        applicable_regs: list[str] = []
        steps: list[RoadmapStep] = []
        step_num = 1

        # ---- CSRD applicability ----
        large_company = (
            employees > 500
            or (employees > 250 and (turnover > 40_000_000 or balance_sheet > 20_000_000))
        )
        sme_listed = listed and employees <= 250

        if large_company or sme_listed:
            applicable_regs.append("CSRD")

            if employees > 500:
                deadline = "2024-01-01 (FY2024 report due 2025)"
            elif large_company:
                deadline = "2025-01-01 (FY2025 report due 2026)"
            else:
                deadline = "2026-01-01 (FY2026 report due 2027)"

            steps.append(RoadmapStep(
                step_number=step_num,
                title="Conduct Double Materiality Assessment (DMA)",
                description=(
                    "Identify and assess which sustainability topics are material from both "
                    "an impact perspective (company's effect on society/environment) and a "
                    "financial perspective (sustainability risks affecting the company). "
                    "This is the foundation of your CSRD sustainability statement."
                ),
                deadline=deadline,
                regulation="CSRD",
                priority="critical",
                articles_cited=["Art.4"],
            ))
            step_num += 1

            steps.append(RoadmapStep(
                step_number=step_num,
                title="Map ESRS disclosure requirements to material topics",
                description=(
                    "Based on your DMA, determine which ESRS standards are applicable: "
                    "E1 (climate), E2 (pollution), E3 (water), E4 (biodiversity), E5 (circular economy), "
                    "S1 (own workforce), S2 (value chain workers), S3 (communities), S4 (consumers), "
                    "G1 (governance). ESRS 1 and ESRS 2 are mandatory for all companies."
                ),
                deadline=deadline,
                regulation="ESRS",
                priority="critical",
                articles_cited=["ESRS_1", "ESRS_2"],
            ))
            step_num += 1

            steps.append(RoadmapStep(
                step_number=step_num,
                title="Establish data collection processes for ESRS KPIs",
                description=(
                    "Set up systems to collect required data: GHG emissions (Scope 1, 2, 3), "
                    "energy consumption, water usage, waste metrics, workforce headcount and "
                    "demographics, health & safety incidents, and governance indicators."
                ),
                deadline=deadline,
                regulation="CSRD",
                priority="high",
                articles_cited=["Art.3", "ESRS_E1", "ESRS_S1"],
            ))
            step_num += 1

            steps.append(RoadmapStep(
                step_number=step_num,
                title="Prepare sustainability statement in management report",
                description=(
                    "Integrate the sustainability statement into the management report, following "
                    "ESRS structure. Ensure ESEF digital tagging for machine-readable submission. "
                    "The statement must include strategy, governance, material impacts/risks/opportunities, "
                    "and metrics & targets sections."
                ),
                deadline=deadline,
                regulation="CSRD",
                priority="critical",
                articles_cited=["Art.3", "Art.9"],
            ))
            step_num += 1

            steps.append(RoadmapStep(
                step_number=step_num,
                title="Obtain limited assurance on sustainability statement",
                description=(
                    "Engage an accredited auditor or certification body to provide limited assurance "
                    "on the sustainability information in the management report, as required by CSRD Art.5."
                ),
                deadline=deadline,
                regulation="CSRD",
                priority="high",
                articles_cited=["Art.5"],
            ))
            step_num += 1

        # ---- EU Taxonomy ----
        if large_company and not is_financial:
            applicable_regs.append("EU_TAXONOMY")
            steps.append(RoadmapStep(
                step_number=step_num,
                title="Assess EU Taxonomy eligibility and alignment",
                description=(
                    "Identify economic activities that are taxonomy-eligible (in-scope of the "
                    "Taxonomy Delegated Acts), then assess alignment: substantial contribution to "
                    "one environmental objective, DNSH to others, and minimum social safeguards. "
                    "Disclose % of turnover, CapEx, and OpEx that is taxonomy-aligned."
                ),
                deadline="2024-01-01",
                regulation="EU_TAXONOMY",
                priority="high",
                articles_cited=["Art.3", "Art.8"],
            ))
            step_num += 1

        # ---- SFDR (financial sector) ----
        if is_financial:
            applicable_regs.append("SFDR")
            steps.append(RoadmapStep(
                step_number=step_num,
                title="Classify financial products under SFDR (Art.6/8/9)",
                description=(
                    "Review all financial products and classify them as Article 6 (no sustainability "
                    "claims), Article 8 (promoting ESG characteristics), or Article 9 (sustainable "
                    "investment objective). Update pre-contractual documents and website disclosures "
                    "to reflect the classification."
                ),
                deadline="2021-03-10 (already applicable)",
                regulation="SFDR",
                priority="critical",
                articles_cited=["Art.6", "Art.8", "Art.9"],
            ))
            step_num += 1

            if employees > 500:
                steps.append(RoadmapStep(
                    step_number=step_num,
                    title="Publish Principal Adverse Impact (PAI) statement",
                    description=(
                        "As a large financial market participant (>500 employees), publish an annual "
                        "PAI statement on your website covering the 14 mandatory PAI indicators "
                        "for investee companies, including GHG emissions, carbon footprint, "
                        "biodiversity, water, and social indicators."
                    ),
                    deadline="2023-06-30 (first reference period: 2022)",
                    regulation="SFDR",
                    priority="critical",
                    articles_cited=["Art.4"],
                ))
                step_num += 1

        # ---- Jurisdiction-specific steps ----
        if "germany" in jurisdiction or "de" == jurisdiction:
            steps.append(RoadmapStep(
                step_number=step_num,
                title="Align CSRD reporting with German HGB requirements",
                description=(
                    "Ensure that the CSRD sustainability statement satisfies the integration "
                    "requirements of German HGB §§ 289b-289e. Note the transition from the "
                    "separate non-financial statement (NFS) format to the CSRD-integrated approach. "
                    "Consult the German Accounting Standards Committee (DRSC) guidance."
                ),
                deadline="2025-01-01",
                regulation="CSRD",
                priority="medium",
                articles_cited=["Art.3"],
            ))
            step_num += 1

        # ---- Supply chain steps ----
        if employees > 250:
            steps.append(RoadmapStep(
                step_number=step_num,
                title="Conduct value chain sustainability assessment",
                description=(
                    "Map your upstream and downstream value chain, identify material sustainability "
                    "impacts, and establish data collection from key suppliers. Align with ESRS S2 "
                    "(workers in value chain) and CSRD Art.8 due diligence requirements."
                ),
                deadline="2025-01-01",
                regulation="CSRD",
                priority="medium",
                articles_cited=["Art.8", "ESRS_S2"],
            ))
            step_num += 1

        summary = self._build_summary(company_profile, applicable_regs, steps)

        return ComplianceRoadmap(
            company_profile=company_profile,
            applicable_regulations=applicable_regs,
            steps=steps,
            summary=summary,
        )

    def _build_summary(
        self,
        profile: dict[str, Any],
        regs: list[str],
        steps: list[RoadmapStep],
    ) -> str:
        if not regs:
            return (
                "Based on the provided company profile, no major EU sustainability regulations "
                "appear directly applicable at this time. Review again as regulatory scope "
                "is expanding and thresholds may change."
            )
        critical = [s for s in steps if s.priority == "critical"]
        return (
            f"This company is subject to {len(regs)} regulation(s): {', '.join(regs)}. "
            f"The roadmap contains {len(steps)} compliance step(s), of which "
            f"{len(critical)} are critical priority. "
            f"Begin immediately with the double materiality assessment and "
            f"ESRS data collection infrastructure."
        )
