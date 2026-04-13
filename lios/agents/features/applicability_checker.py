"""
Feature 4 – Applicability Checker.

Answers "Does regulation X apply to my company?" given company profile data.
Implements threshold logic for CSRD, SFDR, EU Taxonomy, and CSDDD.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RegulationType(str, Enum):
    CSRD = "CSRD"
    SFDR = "SFDR"
    EU_TAXONOMY = "EU_TAXONOMY"
    CSDDD = "CSDDD"
    CBAM = "CBAM"


@dataclass
class CompanyProfile:
    """Minimal company data needed for applicability checks."""

    name: str
    employees: int
    turnover_eur: float           # annual net turnover in EUR
    balance_sheet_eur: float      # total assets in EUR
    is_listed: bool = False       # listed on EU regulated market
    is_financial_sector: bool = False
    jurisdiction: str = "EU"      # home member state (ISO 3166-1 alpha-2 or "EU")
    sector: Optional[str] = None  # NACE code


@dataclass
class ApplicabilityResult:
    regulation: str
    applies: bool
    reason: str
    phase_in_year: Optional[int] = None   # first reporting year
    caveats: list[str] = None

    def __post_init__(self):
        if self.caveats is None:
            self.caveats = []


class ApplicabilityChecker:
    """
    Rule-based checker implementing EU sustainability regulation thresholds.

    Rules are based on the official legislative texts (as of 2024).
    """

    def check(
        self,
        profile: CompanyProfile,
        regulation: RegulationType,
    ) -> ApplicabilityResult:
        method = getattr(self, f"_check_{regulation.value.lower()}", None)
        if method is None:
            return ApplicabilityResult(
                regulation=regulation.value,
                applies=False,
                reason=f"No applicability rules defined for {regulation.value}.",
            )
        return method(profile)

    def check_all(self, profile: CompanyProfile) -> list[ApplicabilityResult]:
        return [self.check(profile, r) for r in RegulationType]

    # ── CSRD ──────────────────────────────────────────────────────────────────
    def _check_csrd(self, p: CompanyProfile) -> ApplicabilityResult:
        """CSRD Art. 3 – large company definition + phase-in schedule."""
        large = (
            p.employees > 250
            and (p.turnover_eur > 40_000_000 or p.balance_sheet_eur > 20_000_000)
        )
        if p.is_listed and p.employees <= 500:
            return ApplicabilityResult(
                regulation="CSRD",
                applies=True,
                reason="Listed SME – CSRD applies from FY 2026 (Art. 40).",
                phase_in_year=2026,
                caveats=["Listed SMEs may opt out until 2028."],
            )
        if large and p.is_listed:
            return ApplicabilityResult(
                regulation="CSRD",
                applies=True,
                reason="Large listed company – CSRD applies from FY 2024 (Art. 5(1)(a)).",
                phase_in_year=2024,
            )
        if large:
            return ApplicabilityResult(
                regulation="CSRD",
                applies=True,
                reason="Large company (>250 employees, >€40M turnover or >€20M assets) – "
                       "CSRD applies from FY 2025 (Art. 5(1)(b)).",
                phase_in_year=2025,
            )
        return ApplicabilityResult(
            regulation="CSRD",
            applies=False,
            reason="Company does not meet CSRD large-company thresholds (Art. 3).",
            caveats=["May still be subject to value-chain data requests from CSRD-covered entities."],
        )

    # ── SFDR ──────────────────────────────────────────────────────────────────
    def _check_sfdr(self, p: CompanyProfile) -> ApplicabilityResult:
        """SFDR Art. 2(1) – financial market participants."""
        if p.is_financial_sector:
            return ApplicabilityResult(
                regulation="SFDR",
                applies=True,
                reason="Financial market participant – SFDR disclosure obligations apply (Art. 6–11).",
            )
        return ApplicabilityResult(
            regulation="SFDR",
            applies=False,
            reason="SFDR applies only to financial market participants and financial advisers.",
        )

    # ── EU Taxonomy ───────────────────────────────────────────────────────────
    def _check_eu_taxonomy(self, p: CompanyProfile) -> ApplicabilityResult:
        """Taxonomy Regulation Art. 8 – disclosure for NFRD/CSRD entities."""
        large = (
            p.employees > 250
            and (p.turnover_eur > 40_000_000 or p.balance_sheet_eur > 20_000_000)
        )
        if large or p.is_financial_sector:
            return ApplicabilityResult(
                regulation="EU_TAXONOMY",
                applies=True,
                reason="Subject to CSRD / NFRD – must disclose taxonomy alignment (Art. 8).",
            )
        return ApplicabilityResult(
            regulation="EU_TAXONOMY",
            applies=False,
            reason="Taxonomy reporting obligation follows CSRD applicability (Art. 8).",
        )

    # ── CSDDD ─────────────────────────────────────────────────────────────────
    def _check_csddd(self, p: CompanyProfile) -> ApplicabilityResult:
        """CSDDD Art. 2 – large companies in scope."""
        tier1 = p.employees > 1_000 and p.turnover_eur > 450_000_000
        tier2 = p.employees > 500 and p.turnover_eur > 150_000_000
        if tier1:
            return ApplicabilityResult(
                regulation="CSDDD",
                applies=True,
                reason="Tier 1 company – CSDDD applies from 2027 (Art. 2(1)(a)).",
                phase_in_year=2027,
            )
        if tier2:
            return ApplicabilityResult(
                regulation="CSDDD",
                applies=True,
                reason="Tier 2 company – CSDDD applies from 2028 (Art. 2(1)(b)).",
                phase_in_year=2028,
            )
        return ApplicabilityResult(
            regulation="CSDDD",
            applies=False,
            reason="Company is below CSDDD employee/turnover thresholds (Art. 2).",
        )

    # ── CBAM ──────────────────────────────────────────────────────────────────
    def _check_cbam(self, p: CompanyProfile) -> ApplicabilityResult:
        """CBAM – importers of covered goods into the EU."""
        cbam_sectors = {
            "C24",  # Iron & steel
            "C241", "C242", "C243",
            "C20",  # Fertilisers
            "B06",  # Cement, aluminium, electricity, hydrogen
        }
        if p.sector and any(p.sector.startswith(s) for s in cbam_sectors):
            return ApplicabilityResult(
                regulation="CBAM",
                applies=True,
                reason=f"Sector {p.sector} is within CBAM scope (Annex I, Reg. 2023/956).",
                phase_in_year=2026,
            )
        return ApplicabilityResult(
            regulation="CBAM",
            applies=False,
            reason="Company sector not listed in CBAM Annex I.",
        )
