"""
Feature 7 – Structured Legal Breakdown.

Produces a section-by-section breakdown of a regulation suitable for
coursework, internal training, or due-diligence documentation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LegalSection:
    section_id: str            # e.g. "CSRD-S1"
    heading: str               # e.g. "Scope and definitions"
    article_range: str         # e.g. "Art. 1–4"
    summary: str
    key_obligations: list[str] = field(default_factory=list)
    cross_references: list[str] = field(default_factory=list)


@dataclass
class LegalBreakdown:
    regulation: str
    version: str
    sections: list[LegalSection] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "regulation": self.regulation,
            "version": self.version,
            "sections": [
                {
                    "section_id": s.section_id,
                    "heading": s.heading,
                    "article_range": s.article_range,
                    "summary": s.summary,
                    "key_obligations": s.key_obligations,
                    "cross_references": s.cross_references,
                }
                for s in self.sections
            ],
        }


# ── Built-in breakdowns (expandable) ─────────────────────────────────────────
_CSRD_BREAKDOWN = LegalBreakdown(
    regulation="CSRD",
    version="2022/2464",
    sections=[
        LegalSection(
            section_id="CSRD-S1",
            heading="Scope and definitions",
            article_range="Art. 1–4",
            summary="Defines which companies must report and from which financial year.",
            key_obligations=[
                "Large companies (>250 employees, >€40M turnover or >€20M assets): FY 2025",
                "Listed SMEs: FY 2026 (opt-out to 2028)",
                "Non-EU parent companies with EU subsidiaries/branches >€150M: FY 2028",
            ],
            cross_references=["ESRS 1 (general requirements)", "Directive 2013/34/EU Art. 2"],
        ),
        LegalSection(
            section_id="CSRD-S2",
            heading="Sustainability reporting requirements",
            article_range="Art. 19a, 29a",
            summary="Core disclosure obligations covering environment, social and governance topics.",
            key_obligations=[
                "Double materiality assessment (impacts AND financial materiality)",
                "Disclose according to ESRS adopted by the Commission",
                "Report in the management report (not a standalone document)",
            ],
            cross_references=["ESRS E1 (Climate change)", "ESRS S1 (Own workforce)"],
        ),
        LegalSection(
            section_id="CSRD-S3",
            heading="Assurance and digital tagging",
            article_range="Art. 26a, 29b",
            summary="External limited assurance required; reports must be machine-readable.",
            key_obligations=[
                "Statutory auditor or independent assurance provider required",
                "XHTML format with XBRL inline tagging (ESEF taxonomy)",
                "Commission may adopt delegated acts for reasonable assurance (future)",
            ],
            cross_references=["Directive 2006/43/EC (Statutory Audit)"],
        ),
    ],
)

_SFDR_BREAKDOWN = LegalBreakdown(
    regulation="SFDR",
    version="2019/2088",
    sections=[
        LegalSection(
            section_id="SFDR-S1",
            heading="Entity-level disclosures",
            article_range="Art. 3–5",
            summary="Financial market participants must publish sustainability risk policies on websites.",
            key_obligations=[
                "Art. 3: Integration of sustainability risks in investment decisions",
                "Art. 4: Principal Adverse Impacts (PAI) statement (mandatory >500 employees)",
                "Art. 5: Sustainability risks in remuneration policies",
            ],
            cross_references=["SFDR RTS (Reg. 2022/1288)"],
        ),
        LegalSection(
            section_id="SFDR-S2",
            heading="Product-level disclosures",
            article_range="Art. 6–11",
            summary="Three product categories: Art. 6 (standard), Art. 8 (ESG characteristics), Art. 9 (sustainable investment).",
            key_obligations=[
                "Art. 6: Pre-contractual sustainability risk disclosure",
                "Art. 8: Promote environmental/social characteristics + DNSH",
                "Art. 9: Sustainable investment objective + taxonomy alignment",
            ],
            cross_references=["EU Taxonomy Reg. Art. 5 & 6", "ESRS E1"],
        ),
    ],
)

_BREAKDOWNS: dict[str, LegalBreakdown] = {
    "CSRD": _CSRD_BREAKDOWN,
    "SFDR": _SFDR_BREAKDOWN,
}


class LegalBreakdownEngine:
    """Return or generate structured breakdowns of EU sustainability regulations."""

    def get(self, regulation: str) -> Optional[LegalBreakdown]:
        """Return the built-in breakdown for *regulation*, or ``None``."""
        return _BREAKDOWNS.get(regulation.upper())

    def list_available(self) -> list[str]:
        return list(_BREAKDOWNS.keys())

    def register(self, breakdown: LegalBreakdown) -> None:
        """Register a custom breakdown (e.g., from training data or LLM output)."""
        _BREAKDOWNS[breakdown.regulation.upper()] = breakdown
