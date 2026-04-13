# Future Scope

This document captures planned enhancements and research directions for LIOS.
Items are loosely prioritised by impact vs. implementation complexity.

---

## Near-Term (v0.2 – v0.3)

### Multi-language Support
- Translate regulation texts into German, French, Polish, Spanish
- Multi-lingual embeddings (`paraphrase-multilingual-MiniLM-L12-v2`)
- Language-specific national law conflict registry

### Automated KB Refresh
- Scheduled EUR-Lex polling (APScheduler already included in requirements)
- Alert users when a regulation's decay score drops below threshold
- Changelog diff: what changed between two versions of a regulation

### Web UI
- React or Next.js frontend consuming the FastAPI backend
- Interactive compliance dashboard with roadmap Gantt view
- Citation viewer with side-by-side article text

### PDF Report Export
- Generate audit-ready PDF compliance reports (WeasyPrint / ReportLab)
- Include citations, decay scores, conflict map

---

## Medium-Term (v0.4 – v0.6)

### RAG Fine-Tuning
- Fine-tune a retrieval model specifically on EU regulatory structure
- Domain-adapted embeddings outperform generic sentence-transformers
- See `training/` for the infrastructure scaffold

### RLHF with Legal Expert Feedback
- Collect attorney annotations on answer quality
- Use DPO or PPO to align the model toward audit-grade outputs
- Training pipeline in `training/fine_tuning/train.py`

### Expanded Regulation Coverage
- Non-EU national laws (UK SDR, US SEC climate rules, Swiss TCFD)
- Sector-specific regulations (banking: CRR/CRD VI; insurance: Solvency II ESG)
- ESRS individual standards (E1–E5, S1–S4, G1) at article granularity

### Agent Memory
- Short-term session context so follow-up questions don't lose thread
- Long-term user profile: saved company data, previous queries, customised roadmaps

---

## Long-Term Research (v1.0+)

### Reasoning over Legal Graphs
- Build a knowledge graph of regulatory cross-references
- Graph-RAG: traverse article dependencies before answering
- Detect transitive conflicts (Reg A ↔ Reg B ↔ national law)

### Formal Verification
- Encode key legal rules as Z3 SMT constraints
- Verify applicability decisions against formal regulatory logic
- Zero-hallucination guarantee backed by formal proofs

### Multi-Jurisdiction Real-Time Intelligence
- Subscribe to official gazette APIs (EUR-Lex OJ, Bundestag, JORF)
- Real-time regulation amendments pushed to KB automatically
- Conflict registry auto-populated from transposition status database

### LIOS-as-a-Service (Optional Cloud Mode)
- Optional SaaS deployment for teams that don't want local setup
- Multi-tenant SQLite per organisation or PostgreSQL for scale
- End-to-end encryption of all legal queries

### Evaluation Benchmark (Public)
- Release an open-source EU sustainability law QA benchmark dataset
- Enable third-party comparison of legal AI systems
- Collaborate with academic institutions and bar associations

---

## Contributing

See the project README for contribution guidelines.
New regulatory coverage, conflict records, and evaluation datasets are
especially welcome contributions.
