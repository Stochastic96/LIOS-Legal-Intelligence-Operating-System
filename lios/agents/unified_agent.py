"""Unified EU sustainability compliance agent — covers CSRD, ESRS, EU Taxonomy, SFDR, and CS3D."""

from __future__ import annotations

from typing import Any

from lios.agents.base_agent import BaseAgent
from lios.knowledge.regulatory_db import RegulatoryDatabase


class UnifiedComplianceAgent(BaseAgent):
    name = "unified_compliance_agent"
    domain = "eu_sustainability_compliance"
    primary_regulations = ["CSRD", "ESRS", "EU_TAXONOMY", "SFDR", "CS3D"]

    def __init__(self, db: RegulatoryDatabase | None = None) -> None:
        super().__init__(db)

    def _domain_analysis(
        self, query_lower: str, articles: list[dict[str, Any]], context: dict[str, Any]
    ) -> list[str]:
        lines: list[str] = []

        # ── CSRD APPLICABILITY & THRESHOLDS ────────────────────────────────────
        if any(kw in query_lower for kw in [
            "threshold", "applies to", "who must", "applicable", "in scope", "size",
            "employee", "turnover", "balance sheet", "listed", "sme", "phase"
        ]):
            lines.append(
                "CSRD phased applicability:\n"
                "• Phase 1 — Public-interest entities >500 employees: first report FY2024, published 2025.\n"
                "• Phase 2 — Large companies meeting 2 of 3 (>250 employees, >€40M turnover, >€20M balance sheet): FY2025, published 2026.\n"
                "• Phase 3 — Listed SMEs: FY2026, published 2027 (opt-out available until 2028).\n"
                "• Non-EU companies with EU net turnover >€150M must also comply if they have an EU subsidiary or branch."
            )

        # ── DOUBLE MATERIALITY ──────────────────────────────────────────────────
        if any(kw in query_lower for kw in [
            "material", "double material", "impact materiality", "financial materiality",
            "esrs 1", "stakeholder", "assessment"
        ]):
            lines.append(
                "CSRD Art.4 requires a double materiality assessment:\n"
                "• Impact materiality — actual and potential effects of the company on people and environment.\n"
                "• Financial materiality — sustainability risks and opportunities affecting the company's finances.\n"
                "ESRS 1 §§43–67 details the methodology including stakeholder engagement and due diligence linkage. "
                "Both dimensions must be assessed independently before determining which ESRS topics are material."
            )

        # ── CLIMATE / GHG / NET ZERO ────────────────────────────────────────────
        if any(kw in query_lower for kw in [
            "ghg", "greenhouse", "climate", "emission", "scope 1", "scope 2", "scope 3",
            "carbon", "net zero", "decarboni", "paris", "1.5"
        ]):
            lines.append(
                "Under ESRS E1 (Climate Change):\n"
                "• Companies must disclose Scope 1, 2, and 3 GHG emissions in tCO2e.\n"
                "• Scope 3 categories 1–15 (full value chain) are required where material.\n"
                "• A climate transition plan aligned with the Paris Agreement (1.5°C pathway) is required if climate is material.\n"
                "• Science-based, time-bound targets with interim milestones are expected.\n"
                "• CSRD Art.22 specifies the transition plan structure, including CapEx and OpEx alignment."
            )

        # ── EU TAXONOMY ─────────────────────────────────────────────────────────
        if any(kw in query_lower for kw in [
            "taxonomy", "taxonomy-aligned", "taxonomy alignment", "dnsh",
            "sustainable activit", "environmental objective", "kpi", "capex", "opex"
        ]):
            lines.append(
                "EU Taxonomy Regulation requirements:\n"
                "• Activities must: (1) substantially contribute to at least one of 6 environmental objectives;\n"
                "  (2) do no significant harm (DNSH) to the other five objectives;\n"
                "  (3) meet minimum social safeguards (OECD Guidelines, UN Guiding Principles).\n"
                "• Large non-financial companies must disclose Taxonomy-aligned % of turnover, CapEx, and OpEx.\n"
                "• Financial products subject to SFDR must disclose Taxonomy-aligned investment percentages.\n"
                "• The 6 objectives: climate mitigation, climate adaptation, water, circular economy, pollution prevention, biodiversity."
            )

        # ── SFDR — PRODUCT CLASSIFICATION ──────────────────────────────────────
        if any(kw in query_lower for kw in [
            "sfdr", "article 6", "article 8", "article 9", "art.6", "art.8", "art.9",
            "fund", "esg fund", "product classification", "light green", "dark green",
            "financial market participant", "fmp", "investment product"
        ]):
            lines.append(
                "SFDR product classification:\n"
                "• Article 6 — no sustainability claims (must explain why ESG integration is not considered).\n"
                "• Article 8 — promotes environmental or social characteristics ('light green'); distinct disclosure requirements.\n"
                "• Article 9 — sustainable investment objective ('dark green'); must maximise Taxonomy-alignment.\n"
                "Each classification requires pre-contractual (KIID/prospectus), periodic (annual), and website disclosures "
                "using mandatory SFDR RTS Annex templates. A Commission review is underway (2024–2025) that may replace this framework."
            )

        # ── PAI — PRINCIPAL ADVERSE IMPACTS ────────────────────────────────────
        if any(kw in query_lower for kw in [
            "pai", "principal adverse", "adverse impact", "sustainability indicator",
            "mandatory indicator", "entity-level"
        ]):
            lines.append(
                "SFDR Art.4 — Principal Adverse Impact (PAI) reporting:\n"
                "• Financial market participants with >500 employees must publish a PAI statement.\n"
                "• 14 mandatory indicators including: GHG emissions intensity, carbon footprint, fossil fuel exposure,\n"
                "  non-renewable energy consumption, water emissions, hazardous waste, UNGC/OECD violations, board gender diversity.\n"
                "• Smaller entities may comply voluntarily (comply-or-explain basis).\n"
                "• PAI statements must be published by 30 June each year, covering the prior calendar year."
            )

        # ── SUPPLY CHAIN / VALUE CHAIN DUE DILIGENCE ───────────────────────────
        if any(kw in query_lower for kw in [
            "supply chain", "supplier", "due diligence", "value chain",
            "upstream", "downstream", "tier 1", "tier 2"
        ]):
            lines.append(
                "Supply chain due diligence under CSRD and CS3D:\n"
                "• CSRD Art.8 requires disclosure of due diligence processes across the full value chain — upstream and downstream.\n"
                "• Companies must identify, prevent, mitigate, and remediate material adverse sustainability impacts.\n"
                "• Where complete tier-1 supplier data is unavailable, estimates using sector averages are permitted with disclosure.\n"
                "• Scope 3 Category 1 (purchased goods/services) and Category 11 (use of sold products) are typically material."
            )

        # ── CS3D — CORPORATE SUSTAINABILITY DUE DILIGENCE ──────────────────────
        if any(kw in query_lower for kw in [
            "cs3d", "csddd", "corporate due diligence", "mandatory due diligence",
            "human rights due diligence", "director liability", "civil liability"
        ]):
            lines.append(
                "EU Corporate Sustainability Due Diligence Directive (CS3D — adopted June 2024):\n"
                "• Phase 1 (2027): companies >5,000 employees and >€1.5B EU turnover.\n"
                "• Phase 2 (2028): >3,000 employees and >€900M EU turnover.\n"
                "• Phase 3 (2029): >1,000 employees and >€450M EU turnover.\n"
                "• Obligations: due diligence policy, adverse impact identification, remediation, grievance mechanisms, climate transition plan.\n"
                "• Directors have a duty of care obligation; civil liability for harm caused by non-compliance."
            )

        # ── WORKERS IN THE VALUE CHAIN / SOCIAL ────────────────────────────────
        if any(kw in query_lower for kw in [
            "worker", "labour", "labor", "human rights", "esrs s2", "esrs s1",
            "pay gap", "diversity", "gender", "forced labour", "child labour",
            "modern slavery", "trafficking", "fair wage", "collective bargaining"
        ]):
            lines.append(
                "Social standards in ESRS and CS3D:\n"
                "• ESRS S1 (Own Workforce): headcount, gender pay gap, collective bargaining coverage, H&S, training.\n"
                "• ESRS S2 (Workers in the Value Chain): labour rights, health & safety, fair wages for supplier workers.\n"
                "• CS3D mandates human rights due diligence across the supply chain including forced labour and child labour.\n"
                "• EU Forced Labour Regulation (effective 2027): products linked to forced labour can be banned from the EU market.\n"
                "• Links to OECD Guidelines and UN Guiding Principles on Business and Human Rights (UNGPs)."
            )

        # ── BIODIVERSITY ────────────────────────────────────────────────────────
        if any(kw in query_lower for kw in [
            "biodiversity", "nature", "ecosystem", "habitat", "species",
            "esrs e4", "biodiversity-sensitive", "nature loss"
        ]):
            lines.append(
                "ESRS E4 (Biodiversity & Ecosystems):\n"
                "• Companies must identify sites in or near biodiversity-sensitive areas.\n"
                "• Disclose material impacts, dependencies on ecosystem services, and transition plans toward no net loss.\n"
                "• Links to the EU Biodiversity Strategy 2030 and Kunming-Montreal Global Biodiversity Framework (GBF) targets."
            )

        # ── WATER ───────────────────────────────────────────────────────────────
        if any(kw in query_lower for kw in [
            "water", "marine", "ocean", "esrs e3", "water-stressed",
            "withdrawal", "discharge", "water consumption"
        ]):
            lines.append(
                "ESRS E3 (Water & Marine Resources): disclose water consumption, withdrawals, and discharges — "
                "especially in water-stressed areas. ESRS E2 covers pollution prevention for air, water, and soil. "
                "Both connect to EU Taxonomy water-related environmental objectives."
            )

        # ── DEFORESTATION ───────────────────────────────────────────────────────
        if any(kw in query_lower for kw in [
            "deforest", "forest", "eudr", "soy", "cattle", "palm oil",
            "wood", "cocoa", "coffee", "rubber", "land use"
        ]):
            lines.append(
                "EU Deforestation Regulation (EUDR — applies from 30 December 2025):\n"
                "• Prohibits placing on the EU market products linked to deforestation after 31 December 2020.\n"
                "• Covered commodities: cattle, cocoa, coffee, palm oil, soya, wood, rubber and their derived products.\n"
                "• Operators must provide due diligence statements with geolocation data for production areas.\n"
                "• Non-compliance: fines up to 4% of EU turnover and market bans."
            )

        # ── REPORTING & ASSURANCE ───────────────────────────────────────────────
        if any(kw in query_lower for kw in [
            "assur", "audit", "verify", "limited assurance", "esrs", "xbrl",
            "sustainability statement", "management report", "esap", "standard"
        ]):
            lines.append(
                "CSRD reporting and assurance requirements:\n"
                "• Sustainability information must be included in the management report.\n"
                "• Subject to limited assurance by a statutory auditor or accredited independent provider.\n"
                "• Reports must follow ESRS standards and use machine-readable XBRL/iXBRL tagging.\n"
                "• The European Single Access Point (ESAP) will aggregate reports from 2026.\n"
                "• The VSME standard is available for voluntary reporting by non-listed SMEs."
            )

        # ── GREENWASHING ────────────────────────────────────────────────────────
        if any(kw in query_lower for kw in [
            "greenwash", "esg claim", "mislead", "marketing", "claim",
            "green claim", "green claims directive"
        ]):
            lines.append(
                "Greenwashing risk and the EU Green Claims Directive:\n"
                "• SFDR lacks a precise definition of 'sustainable investment', creating reclassification risk for Art.8/9 funds.\n"
                "• ESMA and national NCAs have intensified scrutiny following the 2023 fund reclassification wave.\n"
                "• The EU Green Claims Directive (in progress) will require substantiated, independently verified environmental claims.\n"
                "• All ESG claims in marketing must be accurate, proportionate, and not misleading under existing consumer law."
            )

        if not lines:
            lines.append(
                "Under EU sustainability regulations (CSRD, ESRS, EU Taxonomy, SFDR, CS3D), companies must disclose "
                "material sustainability impacts, risks, and opportunities across environmental, social, and governance topics. "
                "Materiality is determined through a double materiality assessment. "
                "Applicability depends on company size, listing status, and sector."
            )

        return lines
