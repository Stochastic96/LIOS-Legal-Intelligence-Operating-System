"""Jurisdiction Conflict Detection – spots EU vs national law gaps."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Conflict:
    eu_regulation: str
    national_law: str
    jurisdiction: str
    conflict_type: str   # "stricter_national" | "divergent_definition" | "format_difference" | "timeline_difference"
    description: str
    severity: str        # "high" | "medium" | "low"


# Realistic hardcoded conflict database
_CONFLICT_DB: list[Conflict] = [
    Conflict(
        eu_regulation="CSRD",
        national_law="German HGB (§§ 289b-289e)",
        jurisdiction="Germany",
        conflict_type="timeline_difference",
        description=(
            "Germany's HGB already required non-financial reporting for large PIEs (>500 employees) "
            "under the NFRD transposition since 2017. Under CSRD, Germany must extend scope to "
            "all large companies by 2025. The transition from HGB non-financial statements to "
            "CSRD sustainability statements involves different materiality concepts: HGB uses "
            "'necessary for understanding' while CSRD uses double materiality. Companies must "
            "align their existing HGB reporting processes with the broader CSRD requirements."
        ),
        severity="medium",
    ),
    Conflict(
        eu_regulation="CSRD",
        national_law="German HGB § 289c (reporting format)",
        jurisdiction="Germany",
        conflict_type="format_difference",
        description=(
            "HGB allows sustainability information to be presented as a separate report or "
            "within the management report. CSRD mandates integration in the management report "
            "with ESEF digital tagging. German companies must adapt their existing separate "
            "non-financial statement format to comply with the mandatory CSRD management "
            "report integration requirement."
        ),
        severity="low",
    ),
    Conflict(
        eu_regulation="EU_TAXONOMY",
        national_law="French loi PACTE (Plan d'Action pour la Croissance et la Transformation des Entreprises)",
        jurisdiction="France",
        conflict_type="divergent_definition",
        description=(
            "The French loi PACTE (2019) introduced 'entreprise à mission' status and early "
            "sustainability disclosure requirements using a broader definition of 'green activities' "
            "than the EU Taxonomy. French companies classified as 'green' under loi PACTE may "
            "not qualify as taxonomy-aligned under the EU Taxonomy technical screening criteria, "
            "particularly in sectors like agriculture and construction."
        ),
        severity="medium",
    ),
    Conflict(
        eu_regulation="SFDR",
        national_law="German WpHG (Securities Trading Act) § 63 et seq.",
        jurisdiction="Germany",
        conflict_type="format_difference",
        description=(
            "German WpHG requires investment firms to inquire about client sustainability preferences "
            "when providing investment advice (MiFID II suitability). The format and granularity "
            "of sustainability preference questions under WpHG guidance differ from SFDR product "
            "classifications. This creates friction where advisors must map SFDR Art.8/9 products "
            "to client preferences expressed in WpHG/MiFID II suitability assessments."
        ),
        severity="medium",
    ),
    Conflict(
        eu_regulation="CSRD",
        national_law="Dutch Corporate Governance Code",
        jurisdiction="Netherlands",
        conflict_type="stricter_national",
        description=(
            "The Dutch Corporate Governance Code (updated 2022) imposes additional sustainability "
            "governance requirements on listed Dutch companies, including mandatory climate scenario "
            "analysis and board-level sustainability expertise requirements. These go beyond CSRD "
            "baseline requirements and may impose additional burdens on Dutch listed companies "
            "already subject to CSRD."
        ),
        severity="low",
    ),
    Conflict(
        eu_regulation="SFDR",
        national_law="French Plan d'Action Finance Durable",
        jurisdiction="France",
        conflict_type="stricter_national",
        description=(
            "France's Action Plan for Sustainable Finance (2021) imposed PAI reporting obligations "
            "on large French asset managers before SFDR RTS became mandatory. French asset managers "
            "must reconcile their existing French AMF-supervised PAI reporting with the EU SFDR "
            "mandatory PAI indicators, which use different metrics and aggregation methods."
        ),
        severity="medium",
    ),
    Conflict(
        eu_regulation="EU_TAXONOMY",
        national_law="Austrian Umweltzeichen (Eco-label)",
        jurisdiction="Austria",
        conflict_type="divergent_definition",
        description=(
            "Austria's Umweltzeichen eco-label for financial products uses criteria that partially "
            "overlap with but differ from EU Taxonomy technical screening criteria. Austrian "
            "investment funds holding Umweltzeichen may need to separately calculate and disclose "
            "EU Taxonomy alignment, which may show lower alignment than the national eco-label "
            "suggests, creating potential consumer confusion."
        ),
        severity="low",
    ),
    Conflict(
        eu_regulation="CSRD",
        national_law="Spanish Ley 11/2018 (Non-Financial Information)",
        jurisdiction="Spain",
        conflict_type="timeline_difference",
        description=(
            "Spain transposed NFRD via Ley 11/2018 with a lower employee threshold (250+) than "
            "the EU NFRD threshold (500+). Under CSRD, Spanish companies already reporting under "
            "Ley 11/2018 must migrate to ESRS standards. The broader scope of Ley 11/2018 means "
            "more Spanish companies are familiar with non-financial reporting, but the content "
            "requirements change significantly under CSRD double materiality."
        ),
        severity="medium",
    ),
]


class JurisdictionConflictDetector:
    """Detect conflicts between EU regulations and national laws."""

    def __init__(self) -> None:
        self._db = _CONFLICT_DB

    def detect_conflicts(
        self,
        regulation: str,
        jurisdictions: list[str],
    ) -> list[Conflict]:
        """Return conflicts for the given regulation and list of jurisdictions."""
        reg_upper = regulation.upper().replace(" ", "_")
        jur_lower = {j.lower() for j in jurisdictions}

        results: list[Conflict] = []
        for conflict in self._db:
            reg_match = (
                conflict.eu_regulation.upper() == reg_upper
                or reg_upper in conflict.eu_regulation.upper()
            )
            conflict_jur_lower = conflict.jurisdiction.lower()
            jur_match = conflict_jur_lower in jur_lower or any(
                j in conflict_jur_lower for j in jur_lower
            )
            if reg_match and (not jurisdictions or jur_match):
                results.append(conflict)

        return results

    def detect_all_conflicts(self, jurisdictions: list[str]) -> list[Conflict]:
        """Return all conflicts for the given list of jurisdictions."""
        jur_lower = {j.lower() for j in jurisdictions}
        results: list[Conflict] = []
        for conflict in self._db:
            if not jurisdictions or any(
                j in conflict.jurisdiction.lower() for j in jur_lower
            ):
                results.append(conflict)
        return results

    def get_all_known_conflicts(self) -> list[Conflict]:
        return list(self._db)
