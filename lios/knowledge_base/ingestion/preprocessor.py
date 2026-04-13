"""Text chunking and cleaning for knowledge-base ingestion."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from lios.utils.helpers import sha256_hex
from lios.utils.logger import get_logger

logger = get_logger(__name__)

# Article heading patterns (EU law style: "Article 3", "Art. 3(1)")
_ARTICLE_RE = re.compile(r"(?i)(art(?:icle)?\.?\s*\d+[\w()]*)")


@dataclass
class TextChunk:
    chunk_id: str
    regulation_id: str
    article_ref: str | None
    text: str
    char_start: int
    char_end: int


class TextPreprocessor:
    """
    Splits regulation text into overlapping chunks suitable for embedding.

    Parameters
    ----------
    chunk_size:
        Target character length for each chunk.
    overlap:
        Character overlap between consecutive chunks (for context continuity).
    """

    def __init__(self, chunk_size: int = 1_500, overlap: int = 200) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def clean(self, text: str) -> str:
        """Normalise whitespace and remove boilerplate unicode artefacts."""
        text = re.sub(r"\s+", " ", text)
        text = text.replace("\u00a0", " ").replace("\ufeff", "")
        return text.strip()

    def chunk(self, regulation_id: str, text: str) -> list[TextChunk]:
        """Split *text* into overlapping chunks, tagging with article refs."""
        text = self.clean(text)
        chunks: list[TextChunk] = []
        pos = 0
        current_article: str | None = None

        while pos < len(text):
            end = min(pos + self.chunk_size, len(text))
            fragment = text[pos:end]

            # Track article heading within this window
            match = _ARTICLE_RE.search(fragment)
            if match:
                current_article = match.group(0)

            chunk_id = sha256_hex(f"{regulation_id}:{pos}")
            chunks.append(
                TextChunk(
                    chunk_id=chunk_id,
                    regulation_id=regulation_id,
                    article_ref=current_article,
                    text=fragment,
                    char_start=pos,
                    char_end=end,
                )
            )
            pos += self.chunk_size - self.overlap

        logger.debug("Chunked regulation %s into %d chunks", regulation_id, len(chunks))
        return chunks
