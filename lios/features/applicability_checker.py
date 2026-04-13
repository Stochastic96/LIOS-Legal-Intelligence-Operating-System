"""Applicability Checker – determines if a regulation applies to a company."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApplicabilityResult:
    regulation: str
    applicable: bool
    reason: str
    threshold_details: dict[str, Any]
    articles_cited: list[str] = field(default_factory=list)


class ApplicabilityChecker:
    """Check whether a specific regulation applies to a company."""

    def check_applicability(
        self,
        regulation: str,
        company_profile: dict[str, Any],
    ) -> ApplicabilityResult:
        reg_key = regulation.upper().replace(" ", "_").replace("-", "_")
        handler = self._handlers().get(reg_key)
        if handler is None:
            return ApplicabilityResult(
                regulation=regulation,
                applicable=False,
                reason=f"Regulation '{regulation}' is not in LIOS knowledge base.",
                threshold_details={},
            )
        return handler(company_profile)

    # ------------------------------------------------------------------
    # Handlers per regulation
    # ------------------------------------------------------------------

    def _handlers(self) -> dict[str, Any]:
        return {
            "CSRD": self._check_csrd,
            "ESRS": self._check_esrs,
            "EU_TAXONOMY": self._check_eu_taxonomy,
            "SFDR": self._check_sfdr,
        }

    def _check_csrd(self, profile: dict[str, Any]) -> ApplicabilityResult:
        employees = profile.get("employees", 0)
        turnover = profile.get("turnover_eur", 0)
        balance_sheet = profile.get("balance_sheet_eur", 0)
        listed = profile.get("listed", False)

        thresholds = {
            "employees": employees,
            "turnover_eur": turnover,
            "balance_sheet_eur": balance_sheet,
            "listed": listed,
            "threshold_employees_large_pie": 500,
            "threshold_employees_large": 250,
            "threshold_turnover_eur": 40_000_000,
            "threshold_balance_sheet_eur": 20_000_000,
        }

        # Phase 1: Public-interest entities >500 employees
        if employees > 500:
            return ApplicabilityResult(
                regulation="CSRD",
                applicable=True,
                reason=(
                    f"Applicable (Phase 1): Company has {employees} employees (>500). "
                    f"Must report from financial year 2024 (report due 2025)."
                ),
                threshold_details=thresholds,
                articles_cited=["Art.1", "Art.10"],
            )

        # Phase 2: Large companies (meet 2 of 3 criteria)
        criteria_met = sum([
            employees > 250,
            turnover > 40_000_000,
            balance_sheet > 20_000_000,
        ])
        if criteria_met >= 2:
            return ApplicabilityResult(
                regulation="CSRD",
                applicable=True,
                reason=(
                    f"Applicable (Phase 2): Company meets {criteria_met} of 3 'large company' criteria "
                    f"(employees>250: {employees>250}, turnover>40M: {turnover>40_000_000}, "
                    f"balance_sheet>20M: {balance_sheet>20_000_000}). "
                    f"Must report from financial year 2025 (report due 2026)."
                ),
                threshold_details=thresholds,
                articles_cited=["Art.2", "Art.10"],
            )

        # Phase 3: Listed SMEs
        if listed:
            return ApplicabilityResult(
                regulation="CSRD",
                applicable=True,
                reason=(
                    "Applicable (Phase 3): Company is listed on EU regulated market. "
                    "Listed SMEs must report from financial year 2026 (report due 2027), "
                    "with opt-out available until 2028."
                ),
                threshold_details=thresholds,
                articles_cited=["Art.1", "Art.10"],
            )

        return ApplicabilityResult(
            regulation="CSRD",
            applicable=False,
            reason=(
                f"Not applicable: Company does not meet CSRD thresholds. "
                f"employees={employees} (need >500 for phase 1, or >250 with other criteria for phase 2), "
                f"turnover={turnover:,.0f} EUR, balance_sheet={balance_sheet:,.0f} EUR, listed={listed}."
            ),
            threshold_details=thresholds,
            articles_cited=["Art.2"],
        )

    def _check_esrs(self, profile: dict[str, Any]) -> ApplicabilityResult:
        # ESRS applies to companies subject to CSRD
        csrd_result = self._check_csrd(profile)
        if csrd_result.applicable:
            return ApplicabilityResult(
                regulation="ESRS",
                applicable=True,
                reason="Applicable: ESRS applies to all companies subject to CSRD. " + csrd_result.reason,
                threshold_details=csrd_result.threshold_details,
                articles_cited=["ESRS_1", "ESRS_2"],
            )
        return ApplicabilityResult(
            regulation="ESRS",
            applicable=False,
            reason="Not applicable: ESRS follows CSRD scope. " + csrd_result.reason,
            threshold_details=csrd_result.threshold_details,
            articles_cited=["ESRS_1"],
        )

    def _check_eu_taxonomy(self, profile: dict[str, Any]) -> ApplicabilityResult:
        employees = profile.get("employees", 0)
        turnover = profile.get("turnover_eur", 0)
        balance_sheet = profile.get("balance_sheet_eur", 0)
        sector = profile.get("sector", "").lower()
        is_financial = sector in {"finance", "financial services", "asset management", "banking", "insurance"}

        thresholds = {
            "employees": employees,
            "turnover_eur": turnover,
            "is_financial_sector": is_financial,
        }

        # Financial market participants: SFDR applies
        if is_financial:
            return ApplicabilityResult(
                regulation="EU_TAXONOMY",
                applicable=True,
                reason=(
                    "Applicable: Financial market participants must disclose taxonomy alignment "
                    "of their financial products under SFDR Art.5/6 and EU Taxonomy Art.8. "
                    "KPI disclosures (% of taxonomy-aligned investments) are required."
                ),
                threshold_details=thresholds,
                articles_cited=["Art.8"],
            )

        # Non-financial: same as CSRD scope (NFRD/CSRD companies)
        criteria_met = sum([
            employees > 250,
            turnover > 40_000_000,
            balance_sheet > 20_000_000,
        ])
        if criteria_met >= 2 or employees > 500:
            return ApplicabilityResult(
                regulation="EU_TAXONOMY",
                applicable=True,
                reason=(
                    "Applicable: Non-financial companies subject to CSRD must disclose "
                    "taxonomy eligibility and alignment (% of turnover, CapEx, OpEx) "
                    "in their sustainability statement per EU Taxonomy Art.8."
                ),
                threshold_details=thresholds,
                articles_cited=["Art.8", "Art.3"],
            )

        return ApplicabilityResult(
            regulation="EU_TAXONOMY",
            applicable=False,
            reason=(
                "Not directly applicable as mandatory disclosure: Company does not meet "
                "CSRD/NFRD thresholds triggering EU Taxonomy KPI reporting. "
                "Voluntary alignment disclosure is possible."
            ),
            threshold_details=thresholds,
            articles_cited=["Art.8"],
        )

    def _check_sfdr(self, profile: dict[str, Any]) -> ApplicabilityResult:
        sector = profile.get("sector", "").lower()
        employees = profile.get("employees", 0)
        is_fmp = sector in {
            "finance", "financial services", "asset management",
            "banking", "insurance", "investment", "fund",
        }

        thresholds = {
            "employees": employees,
            "sector": sector,
            "is_financial_market_participant": is_fmp,
        }

        if is_fmp:
            pai_mandatory = employees > 500
            return ApplicabilityResult(
                regulation="SFDR",
                applicable=True,
                reason=(
                    f"Applicable: Company is a financial market participant in the '{sector}' sector. "
                    f"Must classify financial products under SFDR Art.6/8/9 and provide pre-contractual "
                    f"and periodic disclosures. "
                    + ("PAI statement is mandatory (>500 employees)." if pai_mandatory
                       else "PAI statement is voluntary but recommended (<500 employees).")
                ),
                threshold_details=thresholds,
                articles_cited=["Art.4", "Art.6", "Art.8", "Art.9"],
            )

        return ApplicabilityResult(
            regulation="SFDR",
            applicable=False,
            reason=(
                f"Not applicable: SFDR applies to financial market participants and financial "
                f"advisers. Company sector '{sector}' is not in scope. "
                f"Non-financial companies are indirectly affected as investee companies "
                f"whose data is used by FMPs for SFDR disclosures."
            ),
            threshold_details=thresholds,
            articles_cited=["Art.2"],
        )
