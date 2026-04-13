"""
training/evaluation/benchmark.py
----------------------------------
Run LIOS against a gold-standard benchmark dataset and report quality metrics.

Benchmark JSONL format:
  {"query": "...", "expected_answer": "...", "regulation": "CSRD", "article": "Art. 19a"}

Usage:
    python training/evaluation/benchmark.py \
        --benchmark training/datasets/benchmark.jsonl
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import typer

from lios.agents.orchestrator import Orchestrator
from lios.training.evaluation.metrics import compute_metrics
from lios.utils.logger import get_logger

app = typer.Typer()
logger = get_logger("benchmark")


@dataclass
class BenchmarkResult:
    query: str
    expected: str
    predicted: str
    consensus_reached: bool
    consensus_score: float
    decay_score: float
    metrics: dict[str, Any] = field(default_factory=dict)


@app.command()
def main(
    benchmark: Path = typer.Argument(..., help="Gold-standard benchmark JSONL file"),
    output: Path = typer.Option(Path("training/evaluation/results.json"), "--output", "-o"),
) -> None:
    """Evaluate LIOS against a gold-standard benchmark dataset."""
    asyncio.run(_run(benchmark, output))


async def _run(benchmark: Path, output: Path) -> None:
    if not benchmark.exists():
        typer.echo(f"Benchmark file not found: {benchmark}", err=True)
        raise typer.Exit(1)

    orchestrator = Orchestrator()
    results: list[BenchmarkResult] = []

    with benchmark.open() as f:
        examples = [json.loads(line) for line in f if line.strip()]

    for i, example in enumerate(examples, start=1):
        query = example["query"]
        expected = example.get("expected_answer", "")
        logger.info("[%d/%d] Evaluating: %s", i, len(examples), query[:60])

        try:
            resp = await orchestrator.handle(query)
            predicted = resp.answer or ""
            metrics = compute_metrics(predicted, expected)
            results.append(
                BenchmarkResult(
                    query=query,
                    expected=expected,
                    predicted=predicted,
                    consensus_reached=resp.consensus_reached,
                    consensus_score=resp.consensus_score,
                    decay_score=resp.decay_score or 0.0,
                    metrics=metrics,
                )
            )
        except Exception as exc:
            logger.error("Failed on query '%s': %s", query[:40], exc)

    # Aggregate
    if results:
        avg_rouge = sum(r.metrics.get("rouge1", 0) for r in results) / len(results)
        consensus_rate = sum(1 for r in results if r.consensus_reached) / len(results)
        avg_decay = sum(r.decay_score for r in results) / len(results)
        summary = {
            "total": len(results),
            "consensus_rate": round(consensus_rate, 4),
            "avg_rouge1": round(avg_rouge, 4),
            "avg_decay_score": round(avg_decay, 4),
        }
        logger.info("Summary: %s", summary)
    else:
        summary = {"total": 0}

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "summary": summary,
                "results": [
                    {
                        "query": r.query,
                        "consensus_reached": r.consensus_reached,
                        "consensus_score": r.consensus_score,
                        "metrics": r.metrics,
                    }
                    for r in results
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    logger.info("✓ Results written to %s", output)


if __name__ == "__main__":
    app()
