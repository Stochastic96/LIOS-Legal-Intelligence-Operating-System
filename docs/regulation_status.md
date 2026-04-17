# LIOS Regulation Status

This document tracks the currency of each regulation's data inside the LIOS
knowledge base. Review and update it whenever an official amendment or
delegated act is published.

---

## How to update a regulation

1. Open the relevant file under `lios/knowledge/regulations/` (e.g. `csrd.py`).
2. Edit the `articles`, `thresholds`, or other structured data to reflect the
   amendment.
3. Update `last_updated` to the amendment's official publication date
   (ISO 8601, e.g. `"2025-03-01"`).
4. Update `review_note` to describe what changed and when the next review is
   expected.
5. Re-build the retrieval corpus:
   ```
   python -m lios.ingestion.build_seed_corpus
   ```
6. Restart the server. The decay scorer and citation engine will automatically
   pick up the new date.

---

## Current status

| Regulation | Version in codebase | `last_updated` | Next expected update | Notes |
|---|---|---|---|---|
| **CSRD** | Directive 2022/2464/EU | 2024-07-25 | 2025 (Omnibus simplification) | Phased application ongoing. Omnibus package may reduce scope for smaller companies. |
| **ESRS** | Commission Delegated Regulation (EU) 2023/2772 | 2024-07-31 | 2026 (sector-specific Set 2) | Set 1 standards adopted Jul 2023. Sector-specific standards (Set 2) in development. |
| **EU Taxonomy** | Regulation (EU) 2020/852 | 2024-06-13 | 2025 (additional sectors) | Complementary Climate Delegated Act (nuclear/gas) in force 2023. Taxonomy KPI reporting fully applies from FY 2024. |
| **SFDR** | Regulation (EU) 2019/2088 | 2024-04-22 | 2025–2026 (SFDR reform) | Level 2 RTS in force Jan 2023. Commission consultation on a revised Art.8/9 label framework is ongoing. |

---

## Official sources

All LIOS answers link directly to these EUR-Lex documents:

| Regulation | EUR-Lex URL |
|---|---|
| CSRD | <https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32022L2464> |
| ESRS | <https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32023R2772> |
| EU Taxonomy | <https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32020R0852> |
| SFDR | <https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32019R2088> |

---

## Freshness scoring

LIOS computes a **decay score** (0–100) for each regulation based on
`last_updated` and today's date.  The score decreases by roughly 1 point per
3.65 days, reaching 0 after one year.

| Score | Label |
|---|---|
| 80–100 | Current |
| 60–79 | Aging |
| 40–59 | Stale |
| 0–39 | Outdated |

The trust label shown under each chat answer uses this score together with the
number of source articles cited to communicate answer reliability to the user.
