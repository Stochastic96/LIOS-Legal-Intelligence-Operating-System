# LIOS Repo Cleanup & Rebuild Plan
## Phase 0: Complete Cleanup & Migration

**Status:** Ready to Execute  
**Total Effort:** 1-2 weeks intensive  
**Outcome:** Clean, focused codebase ready for dual-mode system

---

## 📋 CURRENT STATE AUDIT

### **What We Have**
- 77 Python files (core code)
- 22 test files
- 7 regulation modules (CSRD, ESRS, EU_TAXONOMY, SFDR, GDPR, BGB, StGB)
- Multi-agent system (3 specialist agents + consensus)
- Hybrid retrieval (BM25 + semantic)
- Chat UI with turn capture
- FastAPI backend + Click CLI

### **What Doesn't Align With New Vision**
- ❌ Multiple agent profiles (should be config-driven)
- ❌ Validation scattered across 2+ modules
- ❌ Unused routers and endpoints
- ❌ Reasoning module is thin (can consolidate)
- ❌ Registry pattern for agents (overcomplicated)
- ❌ Test structure is scattered (54 test files across repo)
- ❌ No explicit feedback pipeline
- ❌ No background learning job scheduler
- ❌ No gap detection system

---

## 🗑️ PHASE 0 EXECUTION PLAN

### **STAGE 1: DELETE (Remove Dead Code)**

#### Files to DELETE immediately:

**1. `lios/validation/validator.py`**
- Reason: Validation logic exists in models/validation.py
- Consolidate: Move any unique logic to models/validation.py
- Impact: Remove ~150 lines of redundant code

**2. `lios/agents/registry.py`**
- Reason: Not used; agent discovery should be config-driven
- Consolidate: Move agent instantiation to orchestration/engine.py
- Impact: Remove ~100 lines, simplify agent setup

**3. `lios/reasoning/legal_reasoner.py`** (if minimal)
- Reason: IRAC formatting is simple, belongs in agent base class
- Consolidate: Integrate into agents/base_agent.py
- Impact: Remove file, add ~50 lines to base_agent

**4. Unused API routers (partially):**
   - `lios/api/routers/impact.py` — Check if used
   - `lios/api/routers/dashboard.py` — Check if wired
   - Keep only: `core.py`, `chat.py`
   - Remove others or consolidate

**5. Empty template directories:**
   - `lios/api/templates/` — Confirm if used
   - Remove if not referenced

#### Total Deletion Impact: ~300-400 lines removed

---

### **STAGE 2: CONSOLIDATE (Merge Related Modules)**

#### **Consolidation 1: Validation → Single Source of Truth**

**From:** `lios/validation/validator.py` + `lios/models/validation.py`  
**To:** `lios/models/validation.py`

```python
# lios/models/validation.py will contain:
- ErrorResponse
- CompanyProfile validation
- Query validation
- Any other domain validations
```

**Action:**
1. Read both files
2. Merge into models/validation.py
3. Delete lios/validation/
4. Update all imports

---

#### **Consolidation 2: Reasoning → Base Agent**

**From:** `lios/reasoning/legal_reasoner.py`  
**To:** `lios/agents/base_agent.py`

Move IRAC prompt building into base agent as protected methods:
```python
# In BaseAgent:
def _build_irac_context(query, chunks):
    """Build IRAC-structured prompt from chunks."""
    ...

def _invoke_llm(prompt):
    """Call LLM with IRAC structure."""
    ...
```

**Action:**
1. Read legal_reasoner.py
2. Extract IRAC logic
3. Add to BaseAgent
4. Delete lios/reasoning/

---

#### **Consolidation 3: Retrieval Modules → Unified Interface**

**From:** `hybrid_retriever.py` + `retriever.py` + `embedder.py` + `vector_store.py`  
**To:** `hybrid_retriever.py` (single import point)

```python
# lios/retrieval/hybrid_retriever.py becomes:
class HybridRetriever:  # Main API
    - Uses embedder internally
    - Uses vector_store internally
    - Uses base retriever internally
    - User only imports HybridRetriever

# Delete internal modules or keep as private
retriever.py → kept but private
embedder.py → kept but private  
vector_store.py → kept but private
```

**Action:**
1. Verify imports of each module
2. Move all to private (`_embedder.py` etc)
3. Export only HybridRetriever from __init__.py

---

#### **Consolidation 4: Agents → Config-Driven**

**From:** 3 separate agent classes + registry  
**To:** 1 configurable agent class + domain YAML config

```yaml
# lios/config/domains.yaml
domains:
  sustainability:
    name: "Sustainability & ESG"
    regulations: [CSRD, ESRS, EU_TAXONOMY]
    rules:
      - keyword: "materiality"
        context: "Note: double materiality assessment..."
      - keyword: "ghg"
        context: "ESRS E1 requires..."
    
  finance:
    name: "Finance & SFDR"
    regulations: [SFDR, GDPR]
    rules:
      - keyword: "disclosure"
        context: "SFDR requires..."
```

**Action:**
1. Extract domain rules from agent classes
2. Convert to YAML
3. Create config loader
4. Simplify agent to load config
5. Delete supply_chain_agent.py, finance_agent.py
6. Keep base_agent.py + sustainability_agent.py as template

---

### **STAGE 3: REFACTOR (Improve Architecture)**

#### **1. Orchestration Engine Simplification**

**Current:** Complex routing with multiple feature checks  
**Target:** Clean intent-based routing

```python
# lios/orchestration/engine.py
class OrchestrationEngine:
    def process_query(query: str) -> Response:
        
        # Step 1: Parse & classify
        parsed = self.query_parser.parse(query)
        
        # Step 2: Route to appropriate handler
        if parsed.intent == "simple_question":
            return self.simple_handler(query)
        elif parsed.intent == "conflict_analysis":
            return self.conflict_handler(query)
        
        # Step 3: Aggregate response
        return self.response_aggregator.aggregate(result)
```

**Action:**
1. Reduce orchestration logic
2. Make intent routing explicit
3. Document what each intent triggers

---

#### **2. Chat Training Module Cleanup**

**Current:** JSONL + SQLite both supported  
**Target:** Just SQLite (more robust)

```python
# lios/features/chat_training.py
class ChatStore:  # Single interface
    - Append turn (auto handles DB)
    - Get session history
    - Export JSONL for analysis
```

**Action:**
1. Keep SQLite as primary
2. Add bulk export to JSONL
3. Remove JSONL mode (or make it export-only)

---

### **STAGE 4: TEST CONSOLIDATION**

**Current:** 22 separate test files  
**Target:** Organized by layer (~10-12 files)

```
tests/
├── test_models.py           ← Validation, data models
├── test_knowledge.py        ← Regulatory DB, corpus
├── test_retrieval.py        ← Hybrid retriever, embeddings
├── test_agents.py           ← Agent reasoning
├── test_orchestration.py    ← Engine, routing
├── test_features.py         ← Features (applicability, etc)
├── test_chat.py             ← Chat API + turn storage
├── test_intelligence.py     ← Q classifier, answer synthesis
├── test_llm.py              ← Ollama client
├── conftest.py              ← Shared fixtures
└── integration/
    ├── test_end_to_end.py   ← Full pipeline
    └── test_dual_mode.py    ← Learn + Serve modes
```

**Action:**
1. Review all 22 tests
2. Move by logical layer
3. Keep fixtures in conftest.py
4. Delete redundant/old tests

---

## 📊 BEFORE & AFTER

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Core Python files | 77 | ~50 | -35% |
| Test files | 22 | 12 | -45% |
| Module directories | ~15 | ~12 | -20% |
| Validation files | 2 | 1 | -50% |
| Agent classes | 3 | 1 config-driven | Simpler |
| Code to understand | ~15 KLOC | ~10 KLOC | Much clearer |

---

## 🔄 EXECUTION SEQUENCE

### **Week 1 — Cleanup Phase**

**Day 1-2: Validation Consolidation**
- Merge lios/validation/ → lios/models/validation.py
- Update 20+ imports
- Run tests after each step
- Verify no breakage

**Day 3: Agent Simplification**
- Extract domain rules to YAML
- Create config loader
- Consolidate agents to 1 base class
- Delete unused agent files

**Day 4: Reasoning Consolidation**
- Move legal_reasoner to base_agent
- Delete lios/reasoning/
- Update imports

**Day 5: Retrieval Module Cleanup**
- Make embedder/vector_store/retriever private
- Export only HybridRetriever
- Verify all tests pass

**Day 6-7: Test Consolidation**
- Reorganize test files by layer
- Remove redundant tests
- Verify all tests pass

### **Week 2 — Build New System**

**Day 1-2: Feedback Pipeline Schema**
- Design turn storage with feedback fields
- Add feedback API endpoint
- Create feedback → correction pipeline

**Day 3-4: Dual-Mode Router**
- Implement Serve mode logic
- Implement Learn mode logic
- Add mode switching

**Day 5-7: Chat Interface Update**
- Add feedback UI to responses
- Add "next question" UI for Learn mode
- Add confidence breakdown display

---

## ✅ SUCCESS CRITERIA FOR CLEANUP

After cleanup, repo should:

- ✅ Have no unused imports
- ✅ Have no dead code
- ✅ All tests pass (100%)
- ✅ Core logic < 10 KLOC
- ✅ Agent system is config-driven
- ✅ Validation is in one place
- ✅ Imports are clean (no circular deps)
- ✅ New developer can understand structure in 30 mins

---

## ⚠️ BACKUPS & SAFETY

Before starting cleanup:
1. Create `cleanup-backup` branch
2. Tag current main as `pre-cleanup-v1`
3. Commit after each consolidation
4. Run tests after each major change

If anything breaks:
```bash
git checkout cleanup-backup
# Figure out what went wrong
# Try again with smaller steps
```

---

## 📝 NOTES

- **Don't rewrite**, just reorganize
- **Keep all functionality**, just cleaner structure
- **Test early and often** — catch breakage immediately
- **One consolidation at a time** — easier to revert if needed
- **Document as you go** — make decisions explicit

After cleanup is complete, the new dual-mode system will feel like it naturally belongs in this codebase.
