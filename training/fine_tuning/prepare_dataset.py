"""
training/fine_tuning/prepare_dataset.py
----------------------------------------
Prepare instruction-tuning datasets for fine-tuning an LLM on LIOS queries.

Format produced: JSONL with {"instruction": ..., "input": ..., "output": ...}

Usage:
    python training/fine_tuning/prepare_dataset.py \
        --source training/datasets/raw_qa.jsonl \
        --output training/datasets/instruction_tuning.jsonl
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import typer

from lios.utils.logger import get_logger

app = typer.Typer()
logger = get_logger("prepare_dataset")

_SYSTEM_INSTRUCTION = (
    "You are LIOS, an expert AI system specialising in EU sustainability regulations "
    "(CSRD, ESRS, EU Taxonomy, SFDR, CSDDD). Provide precise, citation-grounded answers. "
    "Never speculate. If uncertain, say so explicitly."
)


def _transform(raw: dict) -> dict:
    """Convert a raw Q&A pair into an instruction-tuning example."""
    return {
        "instruction": _SYSTEM_INSTRUCTION,
        "input": raw.get("question", raw.get("query", "")),
        "output": raw.get("answer", raw.get("response", "")),
        "metadata": {
            "regulation": raw.get("regulation"),
            "article_ref": raw.get("article_ref"),
            "jurisdiction": raw.get("jurisdiction"),
        },
    }


@app.command()
def main(
    source: Path = typer.Argument(..., help="Input JSONL file with Q&A pairs"),
    output: Path = typer.Option(
        Path("training/datasets/instruction_tuning.jsonl"),
        "--output", "-o",
    ),
    min_answer_length: int = typer.Option(50, "--min-answer-length"),
) -> None:
    """Prepare an instruction-tuning dataset from raw Q&A pairs."""
    if not source.exists():
        typer.echo(f"Source file not found: {source}", err=True)
        raise typer.Exit(1)

    output.parent.mkdir(parents=True, exist_ok=True)

    written = skipped = 0
    with source.open() as fin, output.open("w") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Skipping malformed line: %s", line[:80])
                skipped += 1
                continue

            example = _transform(raw)
            if len(example["output"]) < min_answer_length:
                skipped += 1
                continue

            fout.write(json.dumps(example, ensure_ascii=False) + "\n")
            written += 1

    logger.info("✓ Wrote %d examples to %s (%d skipped)", written, output, skipped)


if __name__ == "__main__":
    app()
