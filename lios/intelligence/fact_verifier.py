"""Multi-source fact verification for LIOS legal answers.

:class:`FactVerifier` cross-validates key claims in a generated answer against
multiple retrieved legal chunks to flag potential inaccuracies or unsupported
statements.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VerificationResult:
    """Result of a multi-source fact verification pass.

    Attributes:
        is_grounded:     True when at least one supported claim is found.
        supported_claims: List of claims found in at least one source chunk.
        unsupported_claims: List of claims not corroborated by any chunk.
        cross_source_conflicts: Descriptions of apparent conflicts across sources.
        source_coverage:  Fraction of claims that are grounded (0.0–1.0).
    """

    is_grounded: bool
    supported_claims: list[str] = field(default_factory=list)
    unsupported_claims: list[str] = field(default_factory=list)
    cross_source_conflicts: list[str] = field(default_factory=list)
    source_coverage: float = 0.0


class FactVerifier:
    """Verify answer claims against multiple retrieved legal source chunks.

    The verifier works at a sentence level: each sentence in *answer* that
    contains a legal obligation, date, or named provision is matched against
    the *chunks* used to generate it.  A sentence is considered *supported*
    when at least one chunk contains overlapping legal terms.

    This is a lightweight heuristic verifier, not a full semantic entailment
    system.  It is designed to surface obvious grounding failures quickly
    without requiring an LLM.
    """

    # Minimum overlap of significant tokens to count as "supported"
    _MIN_OVERLAP: int = 2
    # Tokens shorter than this are ignored as stopwords
    _MIN_TOKEN_LEN: int = 4

    # Patterns that identify "claim" sentences worth verifying
    _CLAIM_RE = re.compile(
        r"\b(shall|must|required|obligation|mandatory|applies|"
        r"exempt|penalty|fine|sanction|deadline|from\s+\d{4}|"
        r"art\.|article|regulation|directive)\b",
        re.IGNORECASE,
    )

    def verify(
        self,
        answer: str,
        chunks: list[dict[str, Any]],
    ) -> VerificationResult:
        """Verify *answer* against *chunks*.

        Args:
            answer: The generated answer string to check.
            chunks: The list of source chunk dicts used to produce the answer.

        Returns:
            A :class:`VerificationResult` describing grounding quality.
        """
        if not chunks:
            return VerificationResult(
                is_grounded=False,
                unsupported_claims=["No source chunks provided for verification."],
                source_coverage=0.0,
            )

        claim_sentences = self._extract_claim_sentences(answer)
        if not claim_sentences:
            # No verifiable claims found – treat as grounded (no claims to refute)
            return VerificationResult(
                is_grounded=True,
                source_coverage=1.0,
            )

        chunk_texts = [
            f"{c.get('regulation', '')} {c.get('article', '')} {c.get('title', '')} {c.get('text', '')}"
            for c in chunks
        ]
        chunk_token_sets = [self._tokenize(t) for t in chunk_texts]

        supported: list[str] = []
        unsupported: list[str] = []

        for sentence in claim_sentences:
            s_tokens = self._tokenize(sentence)
            if self._is_supported(s_tokens, chunk_token_sets):
                supported.append(sentence)
            else:
                unsupported.append(sentence)

        conflicts = self._detect_conflicts(chunks)
        total = len(claim_sentences)
        coverage = len(supported) / total if total > 0 else 1.0

        return VerificationResult(
            is_grounded=len(supported) > 0,
            supported_claims=supported,
            unsupported_claims=unsupported,
            cross_source_conflicts=conflicts,
            source_coverage=round(coverage, 3),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_claim_sentences(self, text: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [
            s.strip()
            for s in sentences
            if s.strip() and self._CLAIM_RE.search(s)
        ]

    def _tokenize(self, text: str) -> set[str]:
        return {
            tok.lower()
            for tok in re.findall(r"[a-zA-Z][a-zA-Z0-9]{3,}", text)
        }

    def _is_supported(
        self,
        sentence_tokens: set[str],
        chunk_token_sets: list[set[str]],
    ) -> bool:
        for chunk_tokens in chunk_token_sets:
            overlap = sentence_tokens & chunk_tokens
            if len(overlap) >= self._MIN_OVERLAP:
                return True
        return False

    def _detect_conflicts(self, chunks: list[dict[str, Any]]) -> list[str]:
        """Detect obvious conflicting statements across chunks.

        Currently checks for contradictory applicability signals
        (e.g., one chunk says 'exemption' while another says 'mandatory').
        """
        conflicts: list[str] = []
        texts = [c.get("text", "").lower() for c in chunks]
        labels = [
            f"{c.get('regulation', '')} {c.get('article', '')}".strip()
            for c in chunks
        ]

        mandatory_indices = [
            i for i, t in enumerate(texts)
            if re.search(r"\b(mandatory|shall|must|required)\b", t)
        ]
        exempt_indices = [
            i for i, t in enumerate(texts)
            if re.search(r"\b(exempt|opt.out|not\s+required|excluded)\b", t)
        ]

        if mandatory_indices and exempt_indices:
            mand_labels = [labels[i] for i in mandatory_indices[:2]]
            exempt_labels = [labels[i] for i in exempt_indices[:2]]
            conflicts.append(
                f"Potential conflict: {', '.join(mand_labels)} indicate mandatory "
                f"obligations while {', '.join(exempt_labels)} reference exemptions.  "
                "Verify which provisions apply to your specific context."
            )

        return conflicts
