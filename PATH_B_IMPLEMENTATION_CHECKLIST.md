# Path B: Dual-Mode System Implementation Checklist

**Status:** Learning infrastructure complete and tested ✅  
**Phase:** Building integration layer now

## ✅ COMPLETED: Learning Infrastructure

### Core Modules (All Working)
- ✅ `lios/learning/feedback_handler.py` — Handles ✅❌⚠️📝⭐📚 feedback
- ✅ `lios/learning/gap_detector.py` — Identifies knowledge gaps, generates questions
- ✅ `lios/learning/learning_event_store.py` — SQLite storage for learning events
- ✅ All modules import without errors

### What Each Does

**FeedbackHandler** — Processes user feedback
- Records verified answers (✅ Good)
- Stores corrections (❌ Wrong → correct it)
- Captures instructions (📝 Teach me a rule)
- Marks partial answers (⚠️ Incomplete)
- Bookmarks answers (⭐ Save for later)
- Requests deeper explanations (📚 More detail)

**GapDetector** — Maps what LIOS knows and doesn't know
- 6 knowledge levels: UNKNOWN → SEED → LEARNING → CONNECTED → FUNCTIONAL → MASTERED
- Knows prerequisite topics (CSRD before EU Taxonomy)
- Prioritizes learning by foundational importance
- Generates smart questions for each gap
- Tracks completion percentage

**LearningEventStore** — Persists everything
- SQLite backend (robust, no dependencies)
- Stores feedback, corrections, verified answers, instructions
- Full audit trail (every timestamp, session, event type)
- Export to JSONL for analysis

---

## 🔧 NOW: Integration Layer (This Week)

### 1. Update Dependencies
**File:** `lios/api/dependencies.py`
```python
# Add imports
from lios.learning.feedback_handler import FeedbackHandler
from lios.learning.gap_detector import GapDetector
from lios.learning.learning_event_store import LearningEventStore

# Add singletons
learning_event_store = LearningEventStore()
feedback_handler = FeedbackHandler(learning_event_store)
gap_detector = GapDetector.create_default()
```

### 2. Extend Chat Router
**File:** `lios/api/routers/chat.py`
Add these endpoints:

**a) POST /chat/api/feedback** — Accept user feedback
```python
@router.post("/chat/api/feedback", dependencies=[Depends(require_api_key)])
async def submit_feedback(
    session_id: str,
    query: str,
    answer: str,
    feedback_type: FeedbackType,  # "verified", "wrong", "partial", etc
    feedback_text: Optional[str] = None,
) -> dict[str, Any]:
    """User provides feedback on an answer."""
    # Create feedback event
    # Process it (updates knowledge)
    # Return summary
```

**b) GET /chat/api/learn/next-question** — Get Learn Mode question
```python
@router.get("/chat/api/learn/next-question", dependencies=[Depends(require_api_key)])
def get_next_question(session_id: str) -> dict[str, Any]:
    """LIOS asks what it doesn't know."""
    # Get next gap
    # Generate question
    # Return with topic + question text
    # Mark as "asked" in gap detector
```

**c) GET /chat/api/learn/status** — See knowledge progress
```python
@router.get("/chat/api/learn/status", dependencies=[Depends(require_api_key)])
def get_learn_status(session_id: Optional[str] = None) -> dict[str, Any]:
    """Display knowledge map progress."""
    # Return completion percentage
    # List by level: UNKNOWN, LEARNING, FUNCTIONAL, MASTERED
    # Show today's learning events
```

**d) GET /chat/api/learn/summary** — End-of-session report
```python
@router.get("/chat/api/learn/summary", dependencies=[Depends(require_api_key)])
def get_session_learning_summary(session_id: str) -> dict[str, Any]:
    """Summarize what LIOS learned this session."""
    # Count feedback by type
    # List corrections made
    # List new rules learned
    # Recommend next topics
```

### 3. Update Chat UI Templates
**Files:** `lios/api/templates/chat.html`, `react_chat.html`

Add feedback buttons to answer UI:
```html
<!-- Below each LIOS answer -->
<div class="feedback-controls">
  <button onclick="feedbackButton('verified')">✅ Good</button>
  <button onclick="feedbackButton('wrong')">❌ Wrong</button>
  <button onclick="feedbackButton('partial')">⚠️ Partial</button>
  <button onclick="feedbackButton('instruct')">📝 Instruct</button>
  <button onclick="feedbackButton('save')">⭐ Save</button>
  <button onclick="feedbackButton('deeper')">📚 More</button>
</div>
```

Add Learn Mode switch:
```html
<div class="mode-selector">
  <button class="mode-btn" onclick="switchMode('serve')">
    💬 Serve Mode (Ask Me)
  </button>
  <button class="mode-btn" onclick="switchMode('learn')">
    📚 Learn Mode (Quiz Me)
  </button>
</div>
```

### 4. Extend chat_training.py
**File:** `lios/features/chat_training.py`

Add feedback to ChatTurn:
```python
@dataclass
class ChatTurn:
    # ... existing fields ...
    feedback: Optional[dict[str, Any]] = None  # {"type": "verified", "text": "..."}
    learning_event_id: Optional[str] = None
    confidence_before: Optional[float] = None
    confidence_after: Optional[float] = None
```

---

## 📈 THE FLOW (User Experience)

### Serve Mode (Current)
```
User: "What is CSRD?"
↓
LIOS: "Corporate Sustainability Reporting Directive..."
↓
[✅ Good] [❌ Wrong] [⚠️ Partial] [📝 Instruct] [⭐ Save] [📚 More]
↓
User clicks [✅ Good]
↓
FeedbackHandler records: verified answer
→ Confidence on CSRD raised
→ Stored in learning_events
```

### Learn Mode (New)
```
Morning message shows:
"Knowledge Status: 47% complete
 Last learned: CSRD, ESRS
 Ready to learn: EU Taxonomy"
↓
User clicks [Learn Mode]
↓
LIOS: "I understand CSRD but I'm fuzzy on EU Taxonomy. 
       What is the difference between CSRD and EU Taxonomy?"
↓
User: "CSRD is reporting, Taxonomy is classification. 
       See Article 3 of Taxonomy Regulation."
↓
[Submit]
↓
FeedbackHandler + GapDetector:
→ Corrects EU Taxonomy gap_level to LEARNING
→ Stores the relationship (CSRD links to Taxonomy)
→ Confidence increases
→ Suggests next topic: SFDR
```

---

## 🎯 DELIVERABLES BY END OF WEEK

### Day 1-2: Integration
- [ ] Update dependencies.py with learning singletons
- [ ] Add 4 new chat API endpoints
- [ ] Test endpoints work (manual)

### Day 3-4: Frontend
- [ ] Add feedback buttons to HTML
- [ ] Add mode switcher
- [ ] Test feedback flow end-to-end

### Day 5: Testing
- [ ] Run existing tests (verify no breakage)
- [ ] Write 3 happy-path tests:
  - User verifies answer
  - User corrects answer
  - User gets next question
- [ ] Manual testing: use system for 1 hour

### Day 6-7: Documentation
- [ ] Update README with dual-mode explanation
- [ ] Document feedback types
- [ ] Create user guide (how to use Learn Mode)

---

## 📊 SUCCESS METRICS

After week 1 of integration, you should have:

✅ **Serve Mode + Feedback working**
- User can say "✅ Good" or "❌ Wrong" on answers
- Feedback is stored and counted

✅ **Learn Mode operational**
- LIOS asks smart questions each morning
- Questions based on knowledge gaps
- Questions improve as user teaches it

✅ **Knowledge visualization**
- Can see "47% learned" progress
- Console shows  what topics are in what stage
- Export session as JSON to see growth over time

✅ **Zero breakage**
- All existing tests still pass
- Chat API still works as before
- Backward compatible

---

## 🚀 THEN: Phase 2 (Weeks 2-3)

### Background Regulation Watchdog
- Monitor EUR-Lex daily
- Auto-fetch new regulations
- Detect conflicts with existing knowledge
- Email expert: "3 new EU regulations found"

### Confidence Transparency
- Show confidence breakdown: [source quality] [consensus] [temporal decay]
- Store as JSON in responses

### Multi-Instance Support
- Run separate LIOS for different domains
- EU Law LIOS, US Law LIOS, etc.
- Share feedback learning across instances

---

## 🎬 READY TO START CODING?

Next steps:
1. I extend dependencies.py and chat.py with the 4 new endpoints
2. You test POST /chat/api/feedback works
3. You test GET /chat/api/learn/next-question returns a question
4. You test the learning improves over time

Should I start? Just say "yes" and I'll code it all today.
