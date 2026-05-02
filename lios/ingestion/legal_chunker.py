"""Legal text chunker for EUR-Lex articles.

Splits fetched article text into chunks targeting 400-600 tokens each.
Token count is approximated as ``len(words) * _TOKENS_PER_WORD`` (a reasonable
empirical estimate for English legal prose).

Articles shorter than the minimum target are kept as a single chunk.
Longer articles are split on sentence boundaries when possible, and by
word count as a last resort.
"""

from __future__ import annotations

import re
from typing import Any
import math

from lios.ingestion.models import LegalChunk

# Rough token-per-word estimate for English legal text.
_TOKENS_PER_WORD: float = 1.35

# Target chunk size in tokens.
_TARGET_MIN_TOKENS: int = 400
_TARGET_MAX_TOKENS: int = 600

# Equivalent word-count thresholds.
# Use ceil for _MIN_WORDS (conservative lower bound) and floor for _MAX_WORDS
# (conservative upper bound) so chunks stay within the target token range.
_MIN_WORDS: int = math.ceil(_TARGET_MIN_TOKENS / _TOKENS_PER_WORD)   # ≈ 297
_MAX_WORDS: int = math.floor(_TARGET_MAX_TOKENS / _TOKENS_PER_WORD)  # ≈ 444

# When a trailing text fragment is shorter than this fraction of _MIN_WORDS,
# merge it into the preceding segment rather than creating a tiny stub chunk.
_TRAILING_MERGE_THRESHOLD: int = _MIN_WORDS // 2

# Canonical source URLs for the four supported regulations.
_SOURCE_URLS: dict[str, str] = {
    "CSRD": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32022L2464",
    "ESRS": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32023R2772",
    "EU_TAXONOMY": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32020R0852",
    "SFDR": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32019R2088",
}


def chunk_articles(articles: list[dict[str, Any]]) -> list[LegalChunk]:
    """Convert a list of article dicts into :class:`LegalChunk` objects.

    Each article is either kept as-is (when its word count fits within the
    target range or is shorter) or split into multiple labelled parts.

    Args:
        articles: Output from :func:`~lios.ingestion.eurlex_fetcher.fetch_regulation`.

    Returns:
        A flat list of :class:`LegalChunk` instances.
    """
    chunks: list[LegalChunk] = []
    for article in articles:
        chunks.extend(_chunk_article(article))
    return chunks


def _chunk_article(article: dict[str, Any]) -> list[LegalChunk]:
    """Split a single article dict into one or more :class:`LegalChunk` objects."""
    text = article["text"].strip()
    regulation = article["regulation"]
    article_id = article["article"]
    celex_id = article["celex_id"]
    title = article.get("title", article_id)
    published_date = article.get("published_date", "")
    effective_date = article.get("effective_date", "")
    source_url = _SOURCE_URLS.get(regulation, "https://eur-lex.europa.eu")

    jurisdiction = article.get("jurisdiction", "EU")
    words = text.split()

    # Short or medium article — keep as a single chunk.
    if len(words) <= _MAX_WORDS:
        return [
            _make_chunk(
                text=text,
                regulation=regulation,
                article=article_id,
                celex_id=celex_id,
                title=title,
                source_url=source_url,
                published_date=published_date,
                effective_date=effective_date,
                jurisdiction=jurisdiction,
            )
        ]

    # Long article — split on sentence boundaries then by word count.
    segments = _split_text(text, _MIN_WORDS, _MAX_WORDS)
    n = len(segments)
    return [
        _make_chunk(
            text=seg,
            regulation=regulation,
            article=f"{article_id}_{i}" if n > 1 else article_id,
            celex_id=celex_id,
            title=f"{title} (part {i}/{n})" if n > 1 else title,
            source_url=source_url,
            published_date=published_date,
            effective_date=effective_date,
            jurisdiction=jurisdiction,
        )
        for i, seg in enumerate(segments, start=1)
    ]


def _split_text(text: str, min_words: int, max_words: int) -> list[str]:
    """Split *text* into segments of approximately *min_words*–*max_words* words.

    Prefers splitting at sentence boundaries (period or semicolon followed by
    whitespace).  Falls back to hard word-count splits when sentences are too
    long to fit.
    """
    sentences = re.split(r"(?<=[.;])\s+", text)

    segments: list[str] = []
    current: list[str] = []

    for sentence in sentences:
        s_words = sentence.split()
        if not s_words:
            continue

        # If adding this sentence would exceed the max, flush first.
        if current and len(current) + len(s_words) > max_words:
            if len(current) >= min_words:
                segments.append(" ".join(current))
                current = list(s_words)
                continue
            # Current buffer is still below min: keep accumulating to avoid a
            # tiny stub (we'll split later if needed).

        current.extend(s_words)

    # Flush the remaining buffer.
    if current:
        if segments and len(current) < _TRAILING_MERGE_THRESHOLD:
            # Merge a very short trailing fragment into the previous segment.
            segments[-1] = segments[-1] + " " + " ".join(current)
        else:
            segments.append(" ".join(current))

    # If there is still exactly one overly-long segment (a single huge sentence),
    # force-split it by word count.
    result: list[str] = []
    for seg in segments:
        seg_words = seg.split()
        if len(seg_words) <= max_words:
            result.append(seg)
        else:
            for i in range(0, len(seg_words), max_words):
                result.append(" ".join(seg_words[i : i + max_words]))

    return result or [text]


def _make_chunk(
    *,
    text: str,
    regulation: str,
    article: str,
    celex_id: str,
    title: str,
    source_url: str,
    published_date: str,
    effective_date: str,
    jurisdiction: str = "EU",
) -> LegalChunk:
    return LegalChunk.create(
        source_url=source_url,
        celex_or_doc_id=celex_id,
        jurisdiction=jurisdiction,
        regulation=regulation,
        article=article,
        published_date=published_date,
        effective_date=effective_date,
        title=title,
        text=text,
    )
