# LIOS API Reference

Base URL: `http://localhost:8000`

Interactive docs: `http://localhost:8000/docs` (Swagger UI)

---

## Health

### `GET /health`
Returns server status.

**Response:**
```json
{"status": "ok", "version": "0.1.0"}
```

---

## Compliance

### `POST /compliance/query`
Submit a legal question and receive a consensus-grounded answer.

**Request body:**
```json
{
  "query": "Does CSRD apply to our startup with 300 employees and €50M turnover?",
  "jurisdiction": "DE",
  "top_k": 5
}
```

**Response:**
```json
{
  "query_id": "...",
  "query": "...",
  "answer": "Yes. CSRD applies to your company from FY 2025 (Art. 3, Directive 2022/2464).",
  "consensus_reached": true,
  "consensus_score": 0.82,
  "decay_score": 0.95,
  "decay_label": "FRESH",
  "decay_warning": null,
  "conflict_summary": null,
  "jurisdiction_conflicts": [
    {
      "conflict_id": "CSRD-DE-001",
      "eu_regulation": "CSRD",
      "national_law": "German HGB §289b–§289e",
      "jurisdiction": "DE",
      "severity": "HIGH",
      "description": "..."
    }
  ],
  "citations": [
    {
      "regulation": "CSRD",
      "article": "Art. 3",
      "excerpt": "An undertaking qualifies as large if it exceeds 250 employees...",
      "source_url": "https://eur-lex.europa.eu/...",
      "celex": "32022L2464"
    }
  ],
  "agent_responses": {
    "sustainability": "...",
    "supply_chain": "...",
    "finance": "..."
  }
}
```

---

### `POST /compliance/applicability`
Check whether one or more EU sustainability regulations apply to a company.

**Request body:**
```json
{
  "name": "MyCompany GmbH",
  "employees": 300,
  "turnover_eur": 50000000,
  "balance_sheet_eur": 25000000,
  "is_listed": false,
  "is_financial_sector": false,
  "jurisdiction": "DE",
  "sector": "C24",
  "regulation": "CSRD"
}
```
Omit `"regulation"` to check all regulations at once.

---

### `POST /compliance/roadmap`
Generate a personalised compliance action plan.

**Request body:** Same fields as applicability (without `regulation`).

**Response:** Ordered list of compliance steps with deadlines and priorities.

---

### `GET /compliance/conflicts?query=CSRD&jurisdiction=DE`
Return a cross-jurisdiction conflict map.

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | Regulation name or topic |
| `jurisdiction` | string (optional) | ISO 3166-1 alpha-2 country code |

---

### `GET /compliance/breakdown/{regulation}`
Section-by-section breakdown of a regulation.

Example: `GET /compliance/breakdown/CSRD`

**Available regulations:** `CSRD`, `SFDR`

---

## Knowledge Base

### `POST /kb/ingest`
Ingest a new regulation into the knowledge base.

```json
{
  "title": "CSRD – Directive 2022/2464",
  "short_name": "CSRD",
  "framework": "CSRD",
  "content": "Article 1 – Subject matter...",
  "source_url": "https://eur-lex.europa.eu/...",
  "jurisdiction": "EU"
}
```

### `GET /kb/regulations`
List all indexed regulations.

### `DELETE /kb/regulations/{regulation_id}`
Remove a regulation from the knowledge base.

### `GET /kb/stats`
Return vector store statistics.

### `GET /kb/search?query=CSRD+scope&top_k=5`
Semantic search across the knowledge base.
