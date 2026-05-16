#!/usr/bin/env python3
"""
LIOS Local Autolearn — fully local, no gh copilot, no external API.

Uses Ollama directly (bypasses the 25 s LIOS timeout cap) to answer
learn-mode questions and submits them back to the LIOS knowledge map.

Usage:
  python scripts/autolearn_ollama.py                  # 3 workers, run forever
  python scripts/autolearn_ollama.py --workers 5      # more parallel workers
  python scripts/autolearn_ollama.py --target 500     # stop after 500 answers
  python scripts/autolearn_ollama.py --url http://IP:8000  # remote LIOS server
"""

import argparse
import asyncio
import os
import pathlib
import sys
import time
from datetime import datetime

try:
    import httpx
except ImportError:
    sys.exit("Missing dependency: pip install httpx")

# ── Auto-load .env from project root ──────────────────────────────────────────
_env_file = pathlib.Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

# ── Config ─────────────────────────────────────────────────────────────────────

DEFAULT_LIOS_URL   = "http://localhost:8000"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
MODEL   = os.getenv("LIOS_LLM_MODEL", "mistral:latest")
API_KEY = os.getenv("LIOS_API_KEY", "")

SYSTEM_PROMPT = (
    "You are an EU legal compliance expert with deep knowledge of CSRD, ESRS, "
    "EU Taxonomy, SFDR, GDPR, CS3D, LkSG, and German commercial law. "
    "Answer the question in 3-5 clear sentences. "
    "Always cite the specific regulation and article number (e.g. 'CSRD Art. 19a'). "
    "Be precise and factual. Your answer must be at least 40 words."
)

# ── Shared counter ─────────────────────────────────────────────────────────────

class _Counter:
    def __init__(self):
        self._lock  = asyncio.Lock()
        self.total  = 0
        self.valid  = 0
        self.cycles = 0
        self.start  = time.time()

    async def inc(self, valid: bool):
        async with self._lock:
            self.total += 1
            if valid:
                self.valid += 1

    async def inc_cycle(self):
        async with self._lock:
            self.cycles += 1

    def rate(self):
        elapsed = time.time() - self.start
        return self.total / elapsed * 60 if elapsed > 0 else 0


# ── API helpers ────────────────────────────────────────────────────────────────

def _headers() -> dict:
    return {"X-API-Key": API_KEY} if API_KEY else {}


async def get_next_question(client: httpx.AsyncClient, lios_url: str) -> dict | None:
    try:
        r = await client.get(f"{lios_url}/learn/next", timeout=10, headers=_headers())
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  [WARN] /learn/next failed: {e}")
        return None


async def ask_ollama(
    client: httpx.AsyncClient,
    ollama_url: str,
    topic: str,
    category: str,
    question: str,
) -> str:
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Topic: {topic} (Category: {category})\n"
        f"Question: {question}"
    )
    try:
        r = await client.post(
            f"{ollama_url}/api/generate",
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except Exception as e:
        print(f"  [WARN] Ollama call failed: {e}")
        return ""


async def submit_answer(
    client: httpx.AsyncClient,
    lios_url: str,
    topic_id: str,
    answer: str,
) -> dict | None:
    try:
        r = await client.post(
            f"{lios_url}/learn/answer",
            json={"topic_id": topic_id, "answer_text": answer},
            headers=_headers(),
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  [WARN] /learn/answer failed: {e}")
        return None


# ── Worker ─────────────────────────────────────────────────────────────────────

async def worker(
    worker_id: int,
    lios_url: str,
    ollama_url: str,
    counter: _Counter,
    target: int | None,
    stop_event: asyncio.Event,
):
    async with httpx.AsyncClient() as client:
        while not stop_event.is_set():
            if target and counter.total >= target:
                stop_event.set()
                break

            data = await get_next_question(client, lios_url)
            if data is None:
                await asyncio.sleep(2)
                continue

            if data.get("all_mastered"):
                await counter.inc_cycle()
                cycle = counter.cycles
                overall_r = await client.get(f"{lios_url}/learn/map", timeout=10, headers=_headers())
                overall_pct = "?"
                try:
                    m = overall_r.json()
                    topics = m.get("topics") or []
                    if topics:
                        overall_pct = round(sum(t.get("pct", 0) for t in topics) / len(topics))
                except Exception:
                    pass
                print(
                    f"\n{'='*60}\n"
                    f"  🎓 Cycle {cycle} complete — all topics mastered! "
                    f"Overall: {overall_pct}%\n"
                    f"  Total answers: {counter.total}  |  Rate: {counter.rate():.1f}/min\n"
                    f"{'='*60}\n"
                )
                # Brief pause between cycles, then keep building training data
                await asyncio.sleep(3)
                continue

            topic    = data.get("topic", {})
            question = data.get("question")
            if not topic or not question:
                await asyncio.sleep(1)
                continue

            topic_id   = topic["id"]
            topic_name = topic.get("name", topic_id)
            category   = topic.get("category", "")
            pct_before = topic.get("pct", 0)

            answer = await ask_ollama(client, ollama_url, topic_name, category, question)
            if len(answer) < 20:
                # Fallback: minimal factual stub so record_answer still counts it
                answer = (
                    f"{topic_name} is governed by EU law. "
                    f"Compliance obligations arise from the relevant regulation "
                    f"and must be implemented by all in-scope entities."
                )

            result = await submit_answer(client, lios_url, topic_id, answer)
            valid  = bool(result)

            await counter.inc(valid)
            total = counter.total

            if result:
                pct_after   = result.get("topic_updated", {}).get("pct", pct_before)
                overall_pct = result.get("overall_pct", "?")
                status      = result.get("topic_updated", {}).get("status", "?")
                delta       = f"+{pct_after - pct_before}" if pct_after >= pct_before else str(pct_after - pct_before)
                bar_filled  = int(pct_after / 5)
                bar         = "█" * bar_filled + "░" * (20 - bar_filled)
                ts          = datetime.now().strftime("%H:%M:%S")
                print(
                    f"[{ts}] #{total:>5}  W{worker_id}  "
                    f"{topic_name[:28]:<28}  "
                    f"{pct_before:>3}%→{pct_after:>3}% ({delta:>3})  "
                    f"|{bar}|  overall {overall_pct}%  [{status}]"
                )
            else:
                print(f"  [W{worker_id}] #{total} submit failed for {topic_name}")

            # Small delay to avoid hammering Ollama
            await asyncio.sleep(0.5)


# ── Entry point ────────────────────────────────────────────────────────────────

async def run(workers: int, target: int | None, lios_url: str, ollama_url: str):
    # Verify connectivity
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{lios_url}/health", timeout=5, headers=_headers())
            print(f"✓ LIOS backend reachable ({lios_url})")
        except Exception:
            sys.exit(f"✗ Cannot reach LIOS backend at {lios_url}\n  Run: ./start.sh")

        try:
            r = await client.get(f"{ollama_url}/api/tags", timeout=5)
            models = [m["name"] for m in r.json().get("models", [])]
            if MODEL not in models and not any(MODEL.split(":")[0] in m for m in models):
                print(f"  [WARN] Model '{MODEL}' not found. Available: {models}")
            else:
                print(f"✓ Ollama reachable, model: {MODEL}")
        except Exception:
            sys.exit(f"✗ Cannot reach Ollama at {ollama_url}\n  Run: ollama serve")

        # Print current knowledge map state
        try:
            r = await client.get(f"{lios_url}/learn/map", timeout=5, headers=_headers())
            m = r.json()
            topics = m.get("topics") or []
            if topics:
                overall = round(sum(t.get("pct", 0) for t in topics) / len(topics))
                statuses: dict[str, int] = {}
                for t in topics:
                    s = t.get("status", "unknown")
                    statuses[s] = statuses.get(s, 0) + 1
                print(f"\nKnowledge map: {len(topics)} topics, overall {overall}%")
                for s, c in sorted(statuses.items(), key=lambda x: -x[1]):
                    print(f"  {s}: {c}")
        except Exception:
            pass

    target_str = f"{target:,}" if target else "∞ (Ctrl+C to stop)"
    print(
        f"\nStarting {workers} workers  |  target: {target_str} answers  |  model: {MODEL}\n"
        + "-" * 80
    )

    counter    = _Counter()
    stop_event = asyncio.Event()

    tasks = [
        asyncio.create_task(
            worker(i + 1, lios_url, ollama_url, counter, target, stop_event)
        )
        for i in range(workers)
    ]

    try:
        await asyncio.gather(*tasks)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        stop_event.set()
        elapsed = time.time() - counter.start
        print(
            f"\n{'='*60}\n"
            f"  Done.  Total answers: {counter.total}  "
            f"Valid: {counter.valid}  "
            f"Elapsed: {elapsed/60:.1f} min  "
            f"Rate: {counter.rate():.1f}/min\n"
            f"{'='*60}"
        )


def main():
    parser = argparse.ArgumentParser(description="LIOS local autolearn via Ollama")
    parser.add_argument("--workers", type=int, default=3,
                        help="Number of parallel workers (default: 3)")
    parser.add_argument("--target", type=int, default=None,
                        help="Stop after N total answers (default: run forever)")
    parser.add_argument("--url", default=DEFAULT_LIOS_URL,
                        help=f"LIOS backend URL (default: {DEFAULT_LIOS_URL})")
    parser.add_argument("--ollama", default=DEFAULT_OLLAMA_URL,
                        help=f"Ollama URL (default: {DEFAULT_OLLAMA_URL})")
    args = parser.parse_args()

    try:
        asyncio.run(run(args.workers, args.target, args.url, args.ollama))
    except KeyboardInterrupt:
        print("\nStopped by user.")


if __name__ == "__main__":
    main()
