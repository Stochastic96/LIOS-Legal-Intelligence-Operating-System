#!/usr/bin/env python
"""
scripts/ingest_regulations.py
------------------------------
Fetch regulations from EUR-Lex and ingest them into the LIOS knowledge base.

Usage:
    # Fetch and ingest all known regulations:
    python scripts/ingest_regulations.py

    # Ingest a specific regulation by short name:
    python scripts/ingest_regulations.py --regulation CSRD

    # Ingest from a local file:
    python scripts/ingest_regulations.py --file path/to/regulation.txt --short-name CSRD
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import typer

from lios.knowledge_base.ingestion.eurlex_fetcher import EurLexFetcher, KNOWN_REGULATIONS
from lios.knowledge_base.ingestion.document_parser import DocumentParser
from lios.knowledge_base.manager import KnowledgeBaseManager
from lios.knowledge_base.models import Framework
from lios.utils.logger import get_logger

app = typer.Typer()
logger = get_logger("ingest_regulations")


@app.command()
def main(
    regulation: str = typer.Option(None, "--regulation", "-r", help="Short name e.g. CSRD"),
    file: Path = typer.Option(None, "--file", "-f", help="Local file path"),
    short_name: str = typer.Option(None, "--short-name", "-n", help="Short name for local file"),
) -> None:
    """Ingest EU regulations into the LIOS knowledge base."""
    asyncio.run(_run(regulation, file, short_name))


async def _run(
    regulation: str | None,
    file: Path | None,
    short_name: str | None,
) -> None:
    manager = KnowledgeBaseManager()

    if file:
        if not short_name:
            typer.echo("--short-name is required when --file is provided.", err=True)
            raise typer.Exit(1)
        _ingest_file(manager, file, short_name)
        return

    targets = [regulation] if regulation else list(KNOWN_REGULATIONS.keys())
    async with EurLexFetcher() as fetcher:
        for name in targets:
            logger.info("Fetching %s from EUR-Lex…", name)
            try:
                content = await fetcher.fetch_known(name)
                if not content:
                    logger.warning("No content returned for %s – skipping.", name)
                    continue
                framework = Framework(name.upper()) if name.upper() in Framework.__members__ else Framework.OTHER
                reg_id = await manager.ingest(
                    title=f"EUR-Lex: {name}",
                    short_name=name,
                    framework=framework,
                    content=content,
                    jurisdiction="EU",
                )
                logger.info("✓ Ingested %s → id=%s", name, reg_id)
            except Exception as exc:
                logger.error("Failed to ingest %s: %s", name, exc)


async def _ingest_file(manager: KnowledgeBaseManager, file: Path, short_name: str) -> None:
    parser = DocumentParser()
    content = parser.parse(file)
    framework = Framework(short_name.upper()) if short_name.upper() in Framework.__members__ else Framework.OTHER
    reg_id = await manager.ingest(
        title=file.stem,
        short_name=short_name,
        framework=framework,
        content=content,
        source_url=str(file),
    )
    logger.info("✓ Ingested local file %s → id=%s", file.name, reg_id)


if __name__ == "__main__":
    app()
