#!/usr/bin/env python
"""
scripts/export_kb.py
--------------------
Export the LIOS knowledge base to a JSON file for backup or transfer.

Usage:
    python scripts/export_kb.py
    python scripts/export_kb.py --output my_kb_backup.json
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import typer

from lios.knowledge_base.manager import KnowledgeBaseManager
from lios.utils.logger import get_logger

app = typer.Typer()
logger = get_logger("export_kb")


@app.command()
def main(
    output: Path = typer.Option(
        Path("lios_kb_export.json"),
        "--output",
        "-o",
        help="Output JSON file path",
    )
) -> None:
    """Export the LIOS knowledge base to JSON."""
    asyncio.run(_run(output))


async def _run(output: Path) -> None:
    manager = KnowledgeBaseManager()
    regulations = await manager.list_regulations()
    stats = manager.stats()

    export_data = {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "stats": stats,
        "regulations": regulations,
    }

    # Serialise datetime objects
    def default_serialiser(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not JSON-serialisable")

    output.write_text(
        json.dumps(export_data, indent=2, default=default_serialiser),
        encoding="utf-8",
    )
    logger.info("✓ Exported %d regulations to %s", len(regulations), output)


if __name__ == "__main__":
    app()
