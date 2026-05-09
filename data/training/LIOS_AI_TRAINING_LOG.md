# LIOS — AI Training Log
**Purpose**: This file is the authoritative record for any AI agent (Claude, GPT, Gemini, or any future model) working on this project. It explains what LIOS is, what has been built, what the training strategy is, and what to do next. Read this before touching any code.

---

## What Is LIOS?

**LIOS** (Legal Intelligence Operating System) is a RAG-based AI legal assistant that helps companies comply with EU and German law. Its core intelligence is NOT just the LLM — it is the **knowledge corpus** (chunked legal documents) combined with the **content stack** (pre-built expert answers) and the **lawyer-lens system** (5 analytical perspectives applied at ingestion time).

LIOS is designed to answer legal questions like a seasoned EU compliance lawyer — instantly, from known knowledge — without searching the web or hallucinating article numbers.

**Primary users**: Legal teams, compliance officers, CFOs, board members, SME owners operating in the EU.

**Primary domain**: EU sustainability law (CSRD, ESRS, EU Taxonomy, SFDR, CS3D), EU digital law (GDPR, AI Act, NIS2, DORA), German law (HGB, AktG, GmbHG, BGB, LkSG, KSG), EU primary law and CJEU case law.

---

## Architecture Overview

```
User Question
    ↓
[1] Content Stack lookup (< 1ms, no LLM)
    → If hit (confidence ≥ 0.75): return instantly
    ↓ miss
[2] HybridRetriever.search() (BM25 55% + Semantic 30% + Provenance 15%)
    → Returns top-8 chunks from legal_chunks.jsonl
    ↓
[3] select_lens(question) → one of: compliance/risk/drafter/impact/interpretive
    ↓
[4] build_lens_prompt(question, context, lens) → lens-specific LLM prompt
    ↓
[5] LLM call (Ollama local / Azure OpenAI / Groq)
    → IRAC-structured answer
    ↓
[6] FactVerifier — checks answer is grounded in chunks
    ↓
User sees answer
```

---

## The 5 Lawyer Lenses

Every chunk ingested gets annotated with 5 analytical perspectives at ingest time (zero query-time overhead):

| Lens | Professional Perspective | Extracts |
|------|-------------------------|----------|
| `compliance` | Compliance Officer | obligations, thresholds, timelines, triggers |
| `risk` | Risk Manager | penalties, enforcement bodies, liability, monetary amounts |
| `drafter` | Legal Drafter | exact definitions, scope in/out, exceptions |
| `impact` | Business Advisor | affected entities, required actions, deadlines, new obligations |
| `interpretive` | Advocate/Judge | legal principles, CJEU precedent refs, conflicts, Recitals |

**File**: `lios/ingestion/lawyer_lens.py`

---

## The 6 Question Perspectives (for Training)

LIOS is trained to answer from 6 different human perspectives. Every regulation in the knowledge map should have questions from all 6:

| Perspective | Who Asks | What They Need |
|-------------|----------|----------------|
| **Student** | Law student, junior associate | Definitions, principles, case citations, exam-style explanations |
| **Teacher** | Professor, trainer | Teaching examples, analogies, how-it-works explanations |
| **Lawyer** | Practicing attorney, legal counsel | Precise text, article numbers, CJEU cases, exceptions |
| **Business Owner** | CEO, CFO, SME owner | Am I affected? What do I do? By when? What's the cost? |
| **Court** | National court judge | Interpretation, proportionality, precedent, conflicts |
| **European Court** | CJEU advocate/judge | Purposive reading, Recitals, EU principles, direct effect |

---

## The Content Stack

The content stack is a pre-built Q&A database at `data/memory/content_stack.json`.
For every regulation in the corpus, it contains 10 standard entries:

| Q-type | Template |
|--------|----------|
| `what_is` | What is {reg}? |
| `who_affected` | Who must comply with {reg}? |
| `scope_in` | Which companies are in scope of {reg}? |
| `scope_out` | Who is exempt from {reg}? |
| `what_required` | What must companies do under {reg}? |
| `by_when` | What are the key deadlines for {reg}? |
| `penalties` | What are the penalties for non-compliance with {reg}? |
| `key_definitions` | What are the key definitions in {reg}? |
| `interaction` | How does {reg} interact with related regulations? |
| `impact_summary` | What is the business impact of {reg}? |

**File**: `lios/intelligence/content_stack.py`, `lios/intelligence/content_stack_builder.py`

---

## Training Data Strategy

### Phase 1 — Corpus Seeding (DONE)
- 93+ official PDFs ingested into `data/corpus/legal_chunks.jsonl`
- Each chunk annotated with `lens_tags` (5 lenses × 4 fields each)
- Content stack auto-generated from lens_tags

### Phase 2 — Question Bank Expansion (IN PROGRESS)
- Each regulation needs 6-perspective question sets (Student/Teacher/Lawyer/Business/Court/CJEU)
- 10 questions per perspective × 50 regulations = 500 total questions minimum
- Located in: `lios/memory/knowledge_map.py` → `_QUESTION_BANK`
- Target: 30+ questions per regulation (currently avg. ~6)

### Phase 3 — Fine-tuning Dataset (PLANNED)
- Every chat interaction logged to `data/training/chat_training.jsonl`
- Export via `/api/training-export`
- Format: `{"prompt": "...", "completion": "...", "regulation": "CSRD", "qtype": "applicability"}`
- Target: 10,000 supervised examples before first fine-tune run
- Fine-tune script: `scripts/autolearn.py`

### Phase 4 — Copilot Agent (PLANNED)
- A second AI agent that uses LIOS as its knowledge base
- The copilot gets a system prompt instructing it to call LIOS API endpoints
- See "Copilot Agent System Prompt" section below

---

## Knowledge Map — Current State

Tracked in `lios/memory/knowledge_map.py`. 50+ topics across:
- EU-Nachhaltigkeitsrecht (CSRD, ESRS, Taxonomy, SFDR, CS3D, EUDR, Green Deal, IED, REACH)
- EU-Finanzrecht (MiFID II, SRD II, Whistleblower, GDPR, EU Competition)
- Deutsches Recht (LkSG, BEHG, KSG, GmbHG/AktG, HGB, BGB)
- Rechtsgrundlagen (EU terminology, CJEU environment cases, Greenwashing law, Double materiality)
- Globale Rahmenwerke (GRI, TCFD, ISSB/IFRS S1+S2)
- EU-Primärrecht (TEU, TFEU, EU Charter, legislative procedure)
- EuGH-Leitentscheidungen (Van Gend en Loos, Costa, Cassis, Francovich, Schrems, Google Spain)
- EU-Institutionen (Commission, Parliament, CJEU)
- EU-Digitalrecht (AI Act, NIS2)

**Status scale**: unknown → seed → learning → connected → functional → mastered

---

## Files Reference

| Purpose | File |
|---------|------|
| Lawyer-lens annotator | `lios/ingestion/lawyer_lens.py` |
| Content stack store | `lios/intelligence/content_stack.py` |
| Content stack builder | `lios/intelligence/content_stack_builder.py` |
| Lens-specific prompts | `lios/reasoning/lawyer_prompts.py` |
| IRAC reasoning prompt | `lios/reasoning/legal_reasoner.py` |
| Question classifier | `lios/intelligence/question_classifier.py` |
| Answer synthesizer | `lios/intelligence/answer_synthesizer.py` |
| Knowledge map + Q-bank | `lios/memory/knowledge_map.py` |
| Hybrid retriever | `lios/retrieval/hybrid_retriever.py` |
| PDF ingestion | `lios/ingestion/pdf_ingester.py` |
| Batch PDF importer | `scripts/ingest_desktop_pdfs.py` |
| Auto-trainer | `scripts/autolearn.py` |
| API routes | `lios/api/routes.py` |
| Config | `lios/config.py` |

---

## API Endpoints Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/query` | POST | Core RAG query |
| `/chat` | POST | Mobile chat with session |
| `/api/content-stack/{regulation}` | GET | Instant pre-built answers |
| `/api/content-stack/search?q=...` | GET | Keyword search in stack |
| `/api/content-stack` | GET | Stack statistics |
| `/learn/next` | GET | Next learning topic |
| `/learn/answer` | POST | Submit answer, track progress |
| `/learn/map` | GET | Full knowledge map |
| `/intelligence/stats` | GET | Corpus KPIs |
| `/intelligence/corpus` | GET | Per-regulation breakdown |
| `/intelligence/topics` | GET | Per-topic coverage |
| `/intelligence/answers` | GET | Recent answer history |
| `/api/upload` | POST | Upload and index a document |
| `/api/training-export` | GET | Export fine-tuning dataset |
| `/brain/toggle` | POST | Enable/disable LLM |
| `/api/llm-mode` | POST | Switch LLM provider |

---

## What To Do Next (for the next AI reading this)

### Priority 1 — Expand Question Bank to 6 Perspectives
For every regulation in `_QUESTION_BANK` in `lios/memory/knowledge_map.py`, add questions from all 6 perspectives. Use this template:

```python
# CSRD example — current has ~7 questions, needs expansion to 42+
_QUESTION_BANK["csrd"] += [
    # Student perspective
    {"type": "student", "q": "Explain the CSRD in simple terms — what problem does it solve?"},
    {"type": "student", "q": "How does the CSRD relate to the Non-Financial Reporting Directive (NFRD)?"},
    # Teacher perspective
    {"type": "teacher", "q": "Give me a teaching example showing when CSRD applies vs. doesn't apply to an SME."},
    # Lawyer perspective
    {"type": "lawyer", "q": "What is the precise text of CSRD Article 19a paragraph 1 regarding reporting scope?"},
    # Business owner perspective
    {"type": "business_owner", "q": "My company has 280 employees and €55M turnover — do I need a CSRD report for FY2026?"},
    # Court perspective (national)
    {"type": "court", "q": "If a national court must interpret whether an EU subsidiary falls under CSRD consolidation, which rules apply?"},
    # European Court perspective
    {"type": "ecj", "q": "How should CSRD Article 3 be interpreted teleologically in light of Recital 21?"},
]
```

### Priority 2 — Rebuild Content Stack After Corpus Expansion
After expanding question bank and re-ingesting PDFs:
```bash
python3 scripts/ingest_desktop_pdfs.py --stack-only
```

### Priority 3 — Fine-Tuning Dataset Preparation
Generate 10,000 supervised Q&A pairs:
```bash
python3 scripts/autolearn.py --mode pipeline --backend anthropic --limit 10000
```

### Priority 4 — Deploy Copilot Agent
See the copilot system prompt in `data/training/LIOS_COPILOT_SYSTEM_PROMPT.md`

---

## Training Objective

LIOS should be able to:
1. Answer any question about the 50+ regulations in its knowledge map **without LLM** for standard Q-types (content stack hit)
2. Answer with correct article citations **without hallucination** when using LLM
3. Recognize which of the 6 professional perspectives best serves the user
4. Generate follow-up questions that deepen understanding (spaced repetition)
5. Tell the user when it doesn't know and what they should look up

**Success metric**: 90%+ of questions about indexed regulations answered correctly with correct citations, in < 500ms for content stack hits.
