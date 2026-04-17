"""Regulations sub-package.

Shared constants used by the citation engine, ingestion pipeline, and any
other module that needs official EUR-Lex source URLs.
"""

# Canonical EUR-Lex URLs for each supported regulation.
# This is the single source of truth – import from here rather than
# duplicating the mapping in citation_engine.py or build_seed_corpus.py.
REGULATION_BASE_URLS: dict[str, str] = {
    "CSRD": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32022L2464",
    "ESRS": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32023R2772",
    "EU_TAXONOMY": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32020R0852",
    "SFDR": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32019R2088",
}
