"""Document parser – handles plain text, HTML, and PDF inputs."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from lios.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentParser:
    """Parse legal documents from various formats into plain text."""

    def parse(self, source: Union[str, Path]) -> str:
        """
        Parse *source* (file path or raw string) and return clean plain text.

        Supported formats
        -----------------
        - ``.txt``  – returned as-is
        - ``.html`` – stripped via BeautifulSoup
        - ``.pdf``  – extracted via pypdf
        - raw string – returned as-is
        """
        if isinstance(source, str) and "\n" in source:
            return source.strip()

        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Document not found: {path}")

        suffix = path.suffix.lower()
        if suffix == ".txt":
            return path.read_text(encoding="utf-8").strip()
        elif suffix in {".html", ".htm"}:
            return self._parse_html(path.read_text(encoding="utf-8"))
        elif suffix == ".pdf":
            return self._parse_pdf(path)
        else:
            logger.warning("Unknown file type %s – reading as text", suffix)
            return path.read_text(encoding="utf-8").strip()

    # ── Private ───────────────────────────────────────────────────────────────
    @staticmethod
    def _parse_html(html: str) -> str:
        from bs4 import BeautifulSoup  # lazy import

        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    @staticmethod
    def _parse_pdf(path: Path) -> str:
        from pypdf import PdfReader  # lazy import

        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()
