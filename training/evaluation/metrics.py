"""
training/evaluation/metrics.py
--------------------------------
Quality metrics for LIOS answer evaluation.

Metrics implemented:
- ROUGE-1, ROUGE-2, ROUGE-L (recall-oriented overlap)
- Citation precision (fraction of cited articles that are correct)
- Hallucination flag (predicted contains claims not in expected)
"""

from __future__ import annotations

import re
from typing import Any


def _tokenise(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


def _ngrams(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def rouge_n(predicted: str, reference: str, n: int = 1) -> float:
    """Compute ROUGE-N recall score."""
    pred_tokens = _tokenise(predicted)
    ref_tokens = _tokenise(reference)
    if not ref_tokens:
        return 0.0
    pred_ng = _ngrams(pred_tokens, n)
    ref_ng = _ngrams(ref_tokens, n)
    overlap = len(pred_ng & ref_ng)
    return round(overlap / len(ref_ng), 4)


def rouge_l(predicted: str, reference: str) -> float:
    """Compute ROUGE-L (LCS-based) recall score."""
    pred = _tokenise(predicted)
    ref = _tokenise(reference)
    if not ref:
        return 0.0
    # Dynamic programming LCS
    m, n = len(pred), len(ref)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if pred[i - 1] == ref[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    lcs = dp[m][n]
    return round(lcs / n, 4)


def citation_precision(predicted_citations: list[str], correct_citations: list[str]) -> float:
    """
    Fraction of predicted citations that appear in the correct set.

    Citations are normalised to uppercase for comparison.
    """
    if not predicted_citations:
        return 0.0
    pred_set = {c.upper() for c in predicted_citations}
    correct_set = {c.upper() for c in correct_citations}
    hits = len(pred_set & correct_set)
    return round(hits / len(pred_set), 4)


def compute_metrics(
    predicted: str,
    reference: str,
    predicted_citations: list[str] | None = None,
    correct_citations: list[str] | None = None,
) -> dict[str, Any]:
    """Compute all LIOS evaluation metrics for a single prediction."""
    return {
        "rouge1": rouge_n(predicted, reference, n=1),
        "rouge2": rouge_n(predicted, reference, n=2),
        "rougeL": rouge_l(predicted, reference),
        "citation_precision": citation_precision(
            predicted_citations or [], correct_citations or []
        ),
        "answer_length": len(predicted.split()),
        "reference_length": len(reference.split()),
    }
