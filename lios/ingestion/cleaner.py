"""Text cleaning utilities for legal document ingestion."""

from __future__ import annotations

import re


def remove_html(text: str) -> str:
    """Strip HTML/XML tags from *text*.

    Args:
        text: Raw text that may contain HTML markup.

    Returns:
        Plain text with all tags removed.
    """
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"&[a-zA-Z]+;", " ", clean)  # HTML entities
    clean = re.sub(r"&#\d+;", " ", clean)         # Numeric HTML entities
    return clean


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace (spaces, tabs, newlines) to single spaces.

    Args:
        text: Input text.

    Returns:
        Text with normalised whitespace and stripped leading/trailing blanks.
    """
    return re.sub(r"\s+", " ", text).strip()


def clean_text(text: str) -> str:
    """Apply the full cleaning pipeline to *text*.

    Steps:
        1. Remove HTML tags and entities.
        2. Normalise whitespace.

    Args:
        text: Raw input text.

    Returns:
        Cleaned plain text.
    """
    text = remove_html(text)
    text = normalize_whitespace(text)
    return text
