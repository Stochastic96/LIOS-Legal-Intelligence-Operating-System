"""Dynamic answer synthesis from retrieved legal chunks.

:class:`AnswerSynthesizer` builds IRAC-structured answers (Issue / Rule /
Analysis / Conclusion) using the *actual content* of retrieved legal chunks
rather than hard-coded rule templates.  This means every answer is dynamically
composed from the source material, producing answers that vary appropriately
with the query and retrieved context.

Typical usage::

    from lios.intelligence.answer_synthesizer import AnswerSynthesizer

    synthesizer = AnswerSynthesizer()
    answer = synthesizer.synthesize(
        question="What are the penalties for non-compliance with CSRD?",
        chunks=[{"regulation": "CSRD", "article": "Art.7", "title": "Penalties",
                 "text": "Member States shall lay down rules on penalties…", …}],
    )
"""

from __future__ import annotations

import re
from typing import Any

from lios.intelligence.question_classifier import QuestionClassifier, QuestionType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_OBLIGATION_RE = re.compile(
    r"(shall|must|is\s+required|are\s+required|have\s+to|need\s+to|"
    r"obligation\s+to|mandatory)[^.]*\.",
    re.IGNORECASE,
)
_DATE_RE = re.compile(
    r"\b(\d{4}[-/]\d{2}[-/]\d{2}|fy\s*\d{4}|financial\s+year\s+\d{4}|"
    r"from\s+\d{4}|by\s+\d{4}|\d{1,2}\s+\w+\s+\d{4})\b",
    re.IGNORECASE,
)
_PENALTY_RE = re.compile(
    r"(penalt|fine|sanction|dissuasive|proportionate|enforcement)[^.]*\.",
    re.IGNORECASE,
)


def _extract_obligations(text: str) -> list[str]:
    """Extract sentences that describe legal obligations from *text*."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    obligations: list[str] = []
    for sent in sentences:
        sent = sent.strip()
        if sent and _OBLIGATION_RE.search(sent):
            obligations.append(sent)
    return obligations


def _extract_dates(text: str) -> list[str]:
    """Extract date references from *text*."""
    return _DATE_RE.findall(text)


def _extract_penalty_sentences(text: str) -> list[str]:
    """Extract sentences that describe penalties from *text*."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip() and _PENALTY_RE.search(s)]


def _chunk_label(chunk: dict[str, Any]) -> str:
    """Return a human-readable label like 'CSRD Art.4 – Double Materiality'."""
    reg = chunk.get("regulation", "")
    article = chunk.get("article", "")
    title = chunk.get("title", "")
    label = reg
    if article:
        label += f" {article}"
    if title:
        label += f" – {title}"
    return label


def _first_n_sentences(text: str, n: int = 2) -> str:
    """Return the first *n* sentences from *text*."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(s.strip() for s in sentences[:n] if s.strip())


# ---------------------------------------------------------------------------
# AnswerSynthesizer
# ---------------------------------------------------------------------------


class AnswerSynthesizer:
    """Build dynamic IRAC answers from retrieved legal chunks.

    Unlike the rule-based agents which return static template strings, this
    synthesizer uses the actual content of the provided *chunks* to construct
    each answer.  The same query asked with different retrieved chunks will
    produce meaningfully different answers.

    Args:
        classifier: Optional :class:`~lios.intelligence.question_classifier.QuestionClassifier`
            instance.  A default one is created when not supplied.
    """

    def __init__(
        self,
        classifier: QuestionClassifier | None = None,
    ) -> None:
        self._classifier = classifier or QuestionClassifier()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def synthesize(
        self,
        question: str,
        chunks: list[dict[str, Any]],
        *,
        max_chunks: int = 5,
    ) -> str:
        """Synthesize a structured IRAC answer from *question* and *chunks*.

        Args:
            question:   The user's legal question.
            chunks:     Retrieved legal chunk dicts (each having at minimum
                        ``regulation``, ``article``, ``title``, and ``text``).
            max_chunks: Maximum number of chunks to incorporate.

        Returns:
            A formatted IRAC answer string.  Returns a "no context" message
            when *chunks* is empty.
        """
        if not chunks:
            return (
                "No relevant legal context was found in the corpus for this "
                "query.  Please consult the full regulatory text directly."
            )

        qtype = self._classifier.classify(question)
        top = chunks[:max_chunks]

        dispatch = {
            QuestionType.DEFINITION: self._build_definition,
            QuestionType.APPLICABILITY: self._build_applicability,
            QuestionType.REQUIREMENT: self._build_requirement,
            QuestionType.PROCEDURE: self._build_procedure,
            QuestionType.TIMELINE: self._build_timeline,
            QuestionType.COMPARISON: self._build_comparison,
            QuestionType.PENALTY: self._build_penalty,
            QuestionType.GENERAL: self._build_general,
        }
        builder = dispatch.get(qtype, self._build_general)
        return builder(question, top)

    # ------------------------------------------------------------------
    # IRAC builder – shared skeleton
    # ------------------------------------------------------------------

    def _irac(
        self,
        issue: str,
        rules: list[str],
        analysis: str,
        conclusion: str,
        sources: list[str],
    ) -> str:
        """Assemble the final IRAC-formatted string."""
        rule_block = "\n".join(f"  • {r}" for r in rules) if rules else "  • No specific provision identified."
        source_block = " | ".join(sources) if sources else ""
        answer = (
            f"**Issue:** {issue}\n\n"
            f"**Rule:**\n{rule_block}\n\n"
            f"**Analysis:** {analysis}\n\n"
            f"**Conclusion:** {conclusion}"
        )
        if source_block:
            answer += f"\n\n*Sources: {source_block}*"
        return answer

    def _sources_from_chunks(self, chunks: list[dict[str, Any]]) -> list[str]:
        labels: list[str] = []
        seen: set[str] = set()
        for c in chunks:
            lbl = _chunk_label(c)
            if lbl not in seen:
                seen.add(lbl)
                labels.append(lbl)
        return labels

    # ------------------------------------------------------------------
    # Per-type builders
    # ------------------------------------------------------------------

    def _build_definition(self, question: str, chunks: list[dict[str, Any]]) -> str:
        primary = chunks[0]
        label = _chunk_label(primary)
        # Use the first two sentences of the top chunk as the definition
        definition = _first_n_sentences(primary.get("text", ""), n=3)

        additional_context = []
        for c in chunks[1:3]:
            snippet = _first_n_sentences(c.get("text", ""), n=1)
            if snippet:
                additional_context.append(f"{_chunk_label(c)}: {snippet}")

        analysis_parts = [definition]
        if additional_context:
            analysis_parts.append("Additional context: " + "; ".join(additional_context))
        analysis = " ".join(analysis_parts)

        return self._irac(
            issue=question,
            rules=[f"{label} provides the governing definition/description."],
            analysis=analysis,
            conclusion=(
                f"Based on {label}, {_first_n_sentences(primary.get('text', ''), n=1)}"
            ),
            sources=self._sources_from_chunks(chunks[:3]),
        )

    def _build_applicability(self, question: str, chunks: list[dict[str, Any]]) -> str:
        rules: list[str] = []
        analysis_parts: list[str] = []

        for c in chunks[:4]:
            label = _chunk_label(c)
            text = c.get("text", "")
            obligations = _extract_obligations(text)
            if obligations:
                rules.append(f"{label}: {obligations[0]}")
                if len(obligations) > 1:
                    analysis_parts.append(
                        f"Further, {label} specifies: {obligations[1]}"
                    )
            else:
                first_sent = _first_n_sentences(text, n=1)
                if first_sent:
                    rules.append(f"{label}: {first_sent}")

        analysis = " ".join(analysis_parts) if analysis_parts else (
            "Applicability depends on meeting the criteria specified in the "
            "referenced provisions above.  Review the thresholds (e.g., employee "
            "count, turnover, balance sheet size) against your company profile."
        )

        conclusion_text = (
            rules[0].split(": ", 1)[-1] if rules else
            "Confirm whether the specified thresholds and criteria are met."
        )

        return self._irac(
            issue=question,
            rules=rules[:4],
            analysis=analysis,
            conclusion=conclusion_text,
            sources=self._sources_from_chunks(chunks[:4]),
        )

    def _build_requirement(self, question: str, chunks: list[dict[str, Any]]) -> str:
        rules: list[str] = []
        analysis_parts: list[str] = []

        for c in chunks[:5]:
            label = _chunk_label(c)
            text = c.get("text", "")
            obligations = _extract_obligations(text)
            for obl in obligations[:2]:
                rules.append(f"{label}: {obl}")
            if not obligations:
                snippet = _first_n_sentences(text, n=1)
                if snippet:
                    analysis_parts.append(f"{label} is also relevant: {snippet}")

        if analysis_parts:
            analysis = (
                "The obligations above represent the core requirements. "
                + " ".join(analysis_parts)
            )
        else:
            analysis = (
                "Compliance requires fulfilling all of the obligations listed "
                "above.  The specific implementation details are set out in the "
                "referenced provisions and any associated delegated acts or standards."
            )

        rules_summary = (
            f"{len(rules)} obligation(s) identified across "
            f"{len({_chunk_label(c) for c in chunks[:5]})} provision(s)."
        )

        return self._irac(
            issue=question,
            rules=rules[:6],
            analysis=analysis,
            conclusion=rules_summary,
            sources=self._sources_from_chunks(chunks[:5]),
        )

    def _build_procedure(self, question: str, chunks: list[dict[str, Any]]) -> str:
        steps: list[str] = []
        analysis_parts: list[str] = []

        for i, c in enumerate(chunks[:5], start=1):
            label = _chunk_label(c)
            text = c.get("text", "")
            obligations = _extract_obligations(text)
            step_text = obligations[0] if obligations else _first_n_sentences(text, n=1)
            if step_text:
                steps.append(f"Step {i} ({label}): {step_text}")
                if len(obligations) > 1:
                    analysis_parts.append(
                        f"Additionally under {label}: {obligations[1]}"
                    )

        analysis = " ".join(analysis_parts) if analysis_parts else (
            "Follow the steps above sequentially.  Engage qualified legal counsel "
            "and sustainability experts where technical expertise is required."
        )

        return self._irac(
            issue=question,
            rules=steps,
            analysis=analysis,
            conclusion=(
                "Implement the steps above, documenting each stage for audit "
                "purposes.  Verify compliance against the applicable standards "
                "and seek assurance from an accredited third party as required."
            ),
            sources=self._sources_from_chunks(chunks[:5]),
        )

    def _build_timeline(self, question: str, chunks: list[dict[str, Any]]) -> str:
        rules: list[str] = []
        all_dates: list[str] = []

        for c in chunks[:5]:
            label = _chunk_label(c)
            text = c.get("text", "")
            dates = _extract_dates(text)
            if dates:
                all_dates.extend(dates)
                rules.append(
                    f"{label} references the following dates/periods: "
                    + ", ".join(dates[:4])
                )
            else:
                first_sent = _first_n_sentences(text, n=1)
                if first_sent:
                    rules.append(f"{label}: {first_sent}")

        # Deduplicate and sort dates for the analysis
        unique_dates = list(dict.fromkeys(all_dates))
        if unique_dates:
            analysis = (
                f"Key dates identified across the retrieved provisions: "
                + "; ".join(unique_dates[:8])
                + ".  Verify the exact dates with the official regulatory text."
            )
        else:
            analysis = (
                "No explicit dates were extracted from the retrieved provisions.  "
                "Consult the official regulatory text and any national implementing "
                "measures for precise application dates."
            )

        conclusion = (
            "Plan your compliance roadmap around the key dates identified above.  "
            "Allow adequate lead time for data collection, system setup, and "
            "third-party assurance engagement."
        )

        return self._irac(
            issue=question,
            rules=rules[:5],
            analysis=analysis,
            conclusion=conclusion,
            sources=self._sources_from_chunks(chunks[:5]),
        )

    def _build_comparison(self, question: str, chunks: list[dict[str, Any]]) -> str:
        # Group chunks by regulation
        by_reg: dict[str, list[dict[str, Any]]] = {}
        for c in chunks[:6]:
            reg = c.get("regulation", "UNKNOWN")
            by_reg.setdefault(reg, []).append(c)

        rules: list[str] = []
        for reg, reg_chunks in list(by_reg.items())[:3]:
            text = reg_chunks[0].get("text", "")
            snippet = _first_n_sentences(text, n=2)
            if snippet:
                rules.append(f"{_chunk_label(reg_chunks[0])}: {snippet}")

        regs = list(by_reg.keys())
        if len(regs) >= 2:
            analysis = (
                f"Comparing {regs[0]} and {regs[1]}: both regulations govern "
                f"related areas but differ in scope, obligations, and timelines as "
                f"described in the rules above."
            )
        else:
            analysis = "See the rules above for the relevant provisions."

        return self._irac(
            issue=question,
            rules=rules,
            analysis=analysis,
            conclusion=(
                "The regulations referenced above each have distinct scopes and "
                "obligations.  Review the specific provisions for detailed differences."
            ),
            sources=self._sources_from_chunks(chunks[:6]),
        )

    def _build_penalty(self, question: str, chunks: list[dict[str, Any]]) -> str:
        rules: list[str] = []
        analysis_parts: list[str] = []

        for c in chunks[:5]:
            label = _chunk_label(c)
            text = c.get("text", "")
            penalty_sentences = _extract_penalty_sentences(text)
            if penalty_sentences:
                for sent in penalty_sentences[:2]:
                    rules.append(f"{label}: {sent}")
            else:
                first_sent = _first_n_sentences(text, n=1)
                if first_sent:
                    analysis_parts.append(f"{label} is also relevant: {first_sent}")

        if not rules:
            rules = [
                "No specific penalty provision was retrieved.  "
                "Refer to national implementing legislation for penalty details."
            ]

        analysis = " ".join(analysis_parts) if analysis_parts else (
            "Penalties are set by Member States' national implementing legislation.  "
            "They must be effective, proportionate, and dissuasive.  "
            "The specific amounts and procedures vary by jurisdiction."
        )

        return self._irac(
            issue=question,
            rules=rules[:4],
            analysis=analysis,
            conclusion=(
                "Non-compliance may result in the penalties described above.  "
                "Establish robust compliance processes and governance structures "
                "to minimise the risk of infringement."
            ),
            sources=self._sources_from_chunks(chunks[:4]),
        )

    def _build_general(self, question: str, chunks: list[dict[str, Any]]) -> str:
        rules: list[str] = []
        analysis_parts: list[str] = []

        for c in chunks[:5]:
            label = _chunk_label(c)
            text = c.get("text", "")
            obligations = _extract_obligations(text)
            if obligations:
                rules.append(f"{label}: {obligations[0]}")
                analysis_parts.extend(
                    f"{label}: {o}" for o in obligations[1:2]
                )
            else:
                snippet = _first_n_sentences(text, n=2)
                if snippet:
                    rules.append(f"{label}: {snippet}")

        analysis = " ".join(analysis_parts) if analysis_parts else (
            "Review the provisions above in the context of your specific situation.  "
            "The extracted text is sourced directly from the applicable regulations."
        )

        conclusion_text = (
            rules[0].split(": ", 1)[-1][:200] if rules else
            "Consult the referenced provisions and seek qualified legal advice."
        )

        return self._irac(
            issue=question,
            rules=rules[:5],
            analysis=analysis,
            conclusion=conclusion_text,
            sources=self._sources_from_chunks(chunks[:5]),
        )
