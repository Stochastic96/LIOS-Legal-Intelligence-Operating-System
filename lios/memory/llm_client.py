"""Minimal Ollama/OpenAI-compatible LLM client for lios_server."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import httpx

from lios.memory.brain_state import get_base_url, get_model, is_enabled
from lios.memory.store import get_active_rules_as_prompt_block

_CORPUS_FILE = Path("data/corpus/legal_chunks.jsonl")

_SYSTEM_REGULATORY = """\
You are LIOS — a Legal Intelligence Operating System specialising in EU \
sustainability law. Answer questions about CSRD, ESRS, EU Taxonomy, SFDR, \
CS3D, TCFD, ISSB, GRI, greenwashing and related topics.

Rules:
- Lead with the answer, no preamble.
- Cite exact article numbers when you know them (e.g. CSRD Art.19a).
- State confidence: high / medium / low.
- If uncertain, say so. Never invent facts.
- Keep answers under 200 words unless asked for detail.
"""

_SYSTEM_GENERAL = """\
You are LIOS — a helpful AI assistant with expertise in sustainability, ESG, \
climate, and business. Answer clearly and concisely from your training knowledge. \
You don't need to cite specific law articles for general questions, but do mention \
relevant frameworks when useful. Keep answers under 150 words.
"""

_SYSTEM_SMALL_TALK = """\
You are LIOS, a friendly AI assistant. Respond naturally and briefly. \
Don't lecture about sustainability unless the user asks. Be warm and helpful.
"""

# Regulatory keywords that trigger the RAG pipeline
_REGULATORY_KEYWORDS = {
    "csrd", "esrs", "sfdr", "taxonomy", "cs3d", "csddd", "tcfd", "issb",
    "tnfd", "sbti", "gri", "eudr", "lksg", "gdpr", "article", "directive",
    "regulation", "compliance", "mandatory", "threshold", "disclosure",
    "materiality", "double materiality", "scope 1", "scope 2", "scope 3",
    "ghg", "greenwashing", "due diligence", "reporting obligation",
    "sustainability reporting", "esrs e1", "esrs s1", "esrs g1",
    "eu taxonomy", "carbon neutral", "net zero", "net-zero",
}

_SMALL_TALK_PATTERNS = [
    r"^(hi|hello|hey|sup|yo|howdy)\b",
    r"^(good morning|good afternoon|good evening|good night)\b",
    r"^how are you\b",
    r"^what'?s up\b",
    r"^(thanks?|thank you|thx|cheers|great|perfect|cool|nice|awesome)\b",
    r"^(ok|okay|got it|understood|sure|of course|absolutely)\b",
    r"^(bye|goodbye|see you|cya|later|ttyl)\b",
    r"^(yes|no|maybe|nope|yep|yup)\b",
    r"^\?+$",
    r"^(who are you|what are you|what can you do)\b",
    r"^(help|help me)\s*$",
]


def _classify_intent(query: str) -> str:
    """Returns 'small_talk' | 'general_knowledge' | 'regulatory_query'."""
    q = query.lower().strip()

    for pattern in _SMALL_TALK_PATTERNS:
        if re.search(pattern, q):
            return "small_talk"

    for kw in _REGULATORY_KEYWORDS:
        if kw in q:
            return "regulatory_query"

    return "general_knowledge"


def _load_corpus() -> list[dict]:
    if not _CORPUS_FILE.exists():
        return []
    chunks: list[dict] = []
    for line in _CORPUS_FILE.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                chunks.append(json.loads(line))
            except Exception:
                pass
    return chunks


def _retrieve_context(query: str, top_k: int = 5) -> str:
    try:
        from lios.retrieval.chroma_retriever import query as chroma_query
        chunks = chroma_query(query, top_k=top_k)
    except Exception:
        chunks = _keyword_fallback(query, top_k)

    if not chunks:
        return ""

    lines = ["## Relevant legal provisions"]
    for chunk in chunks:
        reg = chunk.get("regulation", "")
        art = chunk.get("article", "")
        text = chunk.get("text", "")
        lines.append(f"[{reg} {art}]: {text}")
    return "\n".join(lines)


def _keyword_fallback(query: str, top_k: int) -> list[dict]:
    chunks = _load_corpus()
    if not chunks:
        return []
    keywords = [w for w in query.lower().split() if len(w) > 3]
    if not keywords:
        return []
    scored = []
    for c in chunks:
        text = (c.get("text", "") + " " + c.get("regulation", "") + " " + c.get("article", "")).lower()
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]


def _call_llm(system: str, messages: list[dict], query: str) -> str | None:
    base_url = get_base_url().rstrip("/")
    model = get_model()

    ollama_messages = [{"role": "system", "content": system}]
    for m in messages[-6:]:
        ollama_messages.append(m)
    ollama_messages.append({"role": "user", "content": query})

    try:
        resp = httpx.post(
            f"{base_url}/v1/chat/completions",
            json={"model": model, "messages": ollama_messages, "stream": False},
            timeout=45.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def chat(
    messages: list[dict[str, str]],
    query: str,
    session_id: str = "default",
) -> dict[str, Any]:
    intent = _classify_intent(query)
    rules_block = get_active_rules_as_prompt_block()
    brain_on = is_enabled()

    # ── Small talk: skip RAG entirely, just respond naturally ────────────────
    if intent == "small_talk":
        if brain_on:
            system = _SYSTEM_SMALL_TALK
            if rules_block:
                system += f"\n\n{rules_block}"
            answer = _call_llm(system, messages, query)
            if answer:
                return {"answer": answer, "confidence": "high", "source": "llm", "brain_used": True}
        return {"answer": _small_talk_fallback(query), "confidence": "high", "source": "fallback", "brain_used": False}

    # ── General knowledge: LLM answers from training, no corpus needed ───────
    if intent == "general_knowledge":
        if brain_on:
            system = _SYSTEM_GENERAL
            if rules_block:
                system += f"\n\n{rules_block}"
            answer = _call_llm(system, messages, query)
            if answer:
                return {"answer": answer, "confidence": "medium", "source": "llm", "brain_used": True}
        return {
            "answer": (
                "Brain is off — turn it on to get LLM-powered answers to general questions. "
                "For specific regulatory questions (CSRD, ESRS, etc.) I can still help from my knowledge base."
            ),
            "confidence": "low",
            "source": "fallback",
            "brain_used": False,
        }

    # ── Regulatory query: LLM first, RAG injects citations on top ───────────
    context = _retrieve_context(query)

    system_parts = [_SYSTEM_REGULATORY]
    if rules_block:
        system_parts.append(rules_block)
    if context:
        system_parts.append(context)
    system = "\n\n".join(system_parts)

    if brain_on:
        answer = _call_llm(system, messages, query)
        if answer:
            return {
                "answer": answer,
                "confidence": "high" if context else "medium",
                "source": "llm+knowledge_base" if context else "llm",
                "brain_used": True,
            }

    # Brain off or LLM failed — fall back to corpus-only answer
    if context:
        chunks_text = context.replace("## Relevant legal provisions\n", "")
        return {
            "answer": f"From my knowledge base:\n\n{chunks_text}\n\n_(Turn Brain ON for a synthesised answer)_",
            "confidence": "medium",
            "source": "knowledge_base",
            "brain_used": False,
        }

    return {
        "answer": "I don't have specific provisions for this in my knowledge base. Turn Brain ON for an LLM-powered answer.",
        "confidence": "low",
        "source": "none",
        "brain_used": False,
    }


def _small_talk_fallback(query: str) -> str:
    q = query.lower().strip()
    if any(w in q for w in ["hi", "hello", "hey"]):
        return "Hello! I'm LIOS, your legal intelligence assistant. Ask me anything about CSRD, ESRS, EU Taxonomy, SFDR, or ESG compliance."
    if any(w in q for w in ["who are you", "what are you"]):
        return "I'm LIOS — a Legal Intelligence Operating System focused on EU sustainability law and ESG compliance. Ask me about CSRD, ESRS, EU Taxonomy, SFDR, and more."
    if any(w in q for w in ["thanks", "thank", "thx", "cheers"]):
        return "You're welcome! Let me know if you have more questions."
    if any(w in q for w in ["bye", "goodbye"]):
        return "Goodbye! Come back anytime for compliance questions."
    if any(w in q for w in ["help"]):
        return "I can help with: CSRD reporting requirements, ESRS standards, EU Taxonomy alignment, SFDR fund classification, ESG materiality, and more. What do you need?"
    return "I'm here! Ask me about EU sustainability law, CSRD, ESRS, or ESG compliance."


def generate_learn_question(topic_name: str, topic_desc: str, existing_pct: int) -> str:
    if not is_enabled():
        return f"Can you explain what {topic_name} is and why it matters for EU sustainability law?"

    base_url = get_base_url().rstrip("/")
    model = get_model()

    prompt = (
        f"You are LIOS, a legal AI student learning about {topic_name} "
        f"({topic_desc}). You currently know {existing_pct}% of this topic. "
        f"Ask ONE specific, focused question to fill a gap in your knowledge. "
        f"Under 40 words. One question only. No preamble."
    )

    try:
        resp = httpx.post(
            f"{base_url}/v1/chat/completions",
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False},
            timeout=20.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return f"Can you explain the key obligations under {topic_name}?"
