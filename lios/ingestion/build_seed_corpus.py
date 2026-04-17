"""Build a provenance-aware JSONL corpus from LIOS built-in regulations.

This is a bootstrap utility for V2 until full external-source ingestion is enabled.
"""

from __future__ import annotations

import json
from pathlib import Path

from lios.ingestion.models import LegalChunk
from lios.knowledge.regulatory_db import RegulatoryDatabase
from lios.knowledge.regulations import REGULATION_BASE_URLS as _BASE_URLS

_CELEX_IDS: dict[str, str] = {
    "CSRD": "32022L2464",
    "ESRS": "32023R2772",
    "EU_TAXONOMY": "32020R0852",
    "SFDR": "32019R2088",
}


def build_seed_corpus(output_path: str | Path = "data/corpus/legal_chunks.jsonl") -> int:
    db = RegulatoryDatabase()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with out.open("w", encoding="utf-8") as f:
        for reg in db.get_all_regulations():
            key = reg["key"]
            full = db.get_regulation(key)
            if not full:
                continue

            for article in full.get("articles", []):
                chunk = LegalChunk.create(
                    source_url=_BASE_URLS.get(key, "https://eur-lex.europa.eu"),
                    celex_or_doc_id=_CELEX_IDS.get(key, key),
                    jurisdiction=(full.get("jurisdictions") or ["EU"])[0],
                    regulation=key,
                    article=article.get("id", "unknown"),
                    published_date=full.get("effective_date", ""),
                    effective_date=full.get("effective_date", ""),
                    title=article.get("title", ""),
                    text=article.get("text", ""),
                )
                f.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")
                count += 1

    return count


if __name__ == "__main__":
    total = build_seed_corpus()
    print(f"Wrote {total} chunks to data/corpus/legal_chunks.jsonl")
