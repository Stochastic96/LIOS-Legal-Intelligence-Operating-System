#!/usr/bin/env python
"""
scripts/setup_kb.py
-------------------
Initialise the LIOS knowledge base from scratch:
  1. Create the SQLite database schema
  2. Initialise the ChromaDB vector store collection
  3. Optionally ingest a seed set of regulations

Usage:
    python scripts/setup_kb.py
    python scripts/setup_kb.py --seed          # also ingest sample data
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent))

import typer

from lios.database.connection import init_db
from lios.knowledge_base.indexing.vector_store import VectorStore
from lios.utils.logger import get_logger

app = typer.Typer()
logger = get_logger("setup_kb")

# ── Sample seed data (built-in, no network required) ─────────────────────────
_SEED_REGULATIONS = [
    {
        "title": "Directive 2022/2464 – Corporate Sustainability Reporting Directive (CSRD)",
        "short_name": "CSRD",
        "framework": "CSRD",
        "content": (
            "Article 1 – Subject matter and amendments to Directive 2013/34/EU. "
            "This Directive lays down rules on the disclosure of information on "
            "sustainability matters by undertakings and groups subject to reporting "
            "obligations under Directive 2013/34/EU.\n"
            "Article 2 – Definitions. For the purposes of this Directive: "
            "'sustainability reporting' means the process of collecting and disclosing "
            "information about sustainability matters in accordance with this Directive.\n"
            "Article 3 – Large undertakings. An undertaking qualifies as large if it "
            "exceeds at least two of the following criteria: "
            "250 employees; net turnover of EUR 40 000 000; "
            "balance sheet total of EUR 20 000 000.\n"
            "Article 19a – Sustainability reporting. Large undertakings shall include "
            "in the management report information necessary to understand the undertaking's "
            "impacts on sustainability matters, and information necessary to understand how "
            "sustainability matters affect the undertaking's development, performance and position."
        ),
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2464",
        "jurisdiction": "EU",
    },
    {
        "title": "Regulation 2019/2088 – Sustainable Finance Disclosure Regulation (SFDR)",
        "short_name": "SFDR",
        "framework": "SFDR",
        "content": (
            "Article 2 – Definitions. 'Sustainability risk' means an environmental, social "
            "or governance event or condition that, if it occurs, could cause an actual or "
            "a potential material negative impact on the value of the investment.\n"
            "Article 3 – Transparency of sustainability risk policies. "
            "Financial market participants shall publish on their websites information about "
            "their policies on the integration of sustainability risks in their "
            "investment decision-making process.\n"
            "Article 4 – Transparency of adverse sustainability impacts at entity level. "
            "Financial market participants shall publish and maintain on their websites "
            "a statement on their due diligence policies with respect to the principal "
            "adverse impacts of investment decisions on sustainability factors.\n"
            "Article 8 – Transparency of the promotion of environmental or social "
            "characteristics in pre-contractual disclosures. "
            "Where a financial product promotes, among other characteristics, environmental "
            "or social characteristics, information on how those characteristics are met "
            "shall be disclosed in the pre-contractual disclosures."
        ),
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32019R2088",
        "jurisdiction": "EU",
    },
    {
        "title": "Regulation 2020/852 – EU Taxonomy Regulation",
        "short_name": "EU_TAXONOMY",
        "framework": "EU_TAXONOMY",
        "content": (
            "Article 1 – Subject matter. This Regulation establishes the criteria for "
            "determining whether an economic activity qualifies as environmentally sustainable "
            "for the purposes of establishing the degree to which an investment is "
            "environmentally sustainable.\n"
            "Article 3 – Criteria for environmentally sustainable economic activities. "
            "An economic activity qualifies as environmentally sustainable where that activity: "
            "(a) contributes substantially to one or more of the environmental objectives; "
            "(b) does not significantly harm any of the environmental objectives (DNSH); "
            "(c) is carried out in compliance with the minimum social safeguards.\n"
            "Article 8 – Disclosure obligations for financial and non-financial undertakings. "
            "Large undertakings subject to Article 19a of Directive 2013/34/EU shall include "
            "in their non-financial statement information on how and to what extent their "
            "activities are associated with environmentally sustainable economic activities."
        ),
        "source_url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32020R0852",
        "jurisdiction": "EU",
    },
]


@app.command()
def main(seed: bool = typer.Option(False, "--seed", help="Ingest sample regulations")) -> None:
    """Initialise the LIOS knowledge base."""
    asyncio.run(_run(seed))


async def _run(seed: bool) -> None:
    logger.info("Initialising database…")
    await init_db()
    logger.info("Database initialised.")

    logger.info("Initialising vector store…")
    vs = VectorStore()
    vs._get_collection()  # triggers lazy init
    logger.info("Vector store ready – %d chunks indexed.", vs.count())

    if seed:
        from lios.knowledge_base.manager import KnowledgeBaseManager
        from lios.knowledge_base.models import Framework

        manager = KnowledgeBaseManager()
        for reg_data in _SEED_REGULATIONS:
            framework = Framework(reg_data["framework"])
            reg_id = await manager.ingest(
                title=reg_data["title"],
                short_name=reg_data["short_name"],
                framework=framework,
                content=reg_data["content"],
                source_url=reg_data.get("source_url"),
                jurisdiction=reg_data.get("jurisdiction", "EU"),
            )
            logger.info("Seeded regulation '%s' → id=%s", reg_data["short_name"], reg_id)

    logger.info("✓ Knowledge base setup complete.")


if __name__ == "__main__":
    app()
