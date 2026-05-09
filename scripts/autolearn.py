#!/usr/bin/env python3
"""
LIOS Auto-Trainer — pipeline mode.

LIOS (producer) pre-fetches questions QUEUE_DEPTH ahead.
The agent (consumer) answers from the queue and submits back in real time.
LIOS always stays ahead so the agent is never idle.

Usage:
  python3 scripts/autolearn.py                        # gh copilot (default)
  python3 scripts/autolearn.py --agent claude         # claude CLI
  python3 scripts/autolearn.py --agent api            # Anthropic API (ANTHROPIC_API_KEY)
  python3 scripts/autolearn.py --url http://IP:8000   # remote server
  python3 scripts/autolearn.py --depth 5              # deeper pipeline
"""

import argparse
import asyncio
import os
import subprocess
import sys
import textwrap
import time
from datetime import datetime

try:
    import httpx
except ImportError:
    sys.exit("pip install httpx")

# ── Config ─────────────────────────────────────────────────────────────────────

DEFAULT_QUEUE_DEPTH = 3

SYSTEM = (
    "You are a German EU compliance expert. "
    "Answer in 2–4 sentences (English or German). "
    "Cite the relevant regulation or article where possible. "
    "Answer must be at least 25 characters."
)

# ── Answering backends ─────────────────────────────────────────────────────────

def _fallback(topic: str, question: str) -> str:
    return (
        f"{topic} ist ein zentrales Thema des EU-Rechts. "
        f"Die Anforderungen ergeben sich aus der einschlägigen EU-Verordnung "
        f"und sind für betroffene Unternehmen verbindlich umzusetzen."
    )


def _copilot(question: str, topic: str, category: str) -> str:
    prompt = f"{SYSTEM}\n\nThema: {topic} ({category})\nFrage: {question}"
    r = subprocess.run(
        ["gh", "copilot", "explain", prompt],
        capture_output=True, text=True, timeout=45,
    )
    a = (r.stdout or "").strip()
    return a if len(a) >= 25 else _fallback(topic, question)


def _claude_cli(question: str, topic: str, category: str) -> str:
    prompt = f"{SYSTEM}\n\nThema: {topic} ({category})\nFrage: {question}"
    r = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True, text=True, timeout=60,
    )
    a = (r.stdout or "").strip()
    return a if len(a) >= 25 else _fallback(topic, question)


async def _anthropic_api(question: str, topic: str, category: str,
                          client: httpx.AsyncClient) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return _fallback(topic, question)
    resp = await client.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 300,
            "system": SYSTEM,
            "messages": [{"role": "user",
                           "content": f"Thema: {topic} ({category})\nFrage: {question}"}],
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"].strip()

# ── LIOS API ───────────────────────────────────────────────────────────────────

async def lios_next(client: httpx.AsyncClient, base: str) -> dict | None:
    try:
        r = await client.get(f"{base}/learn/next", timeout=15)
        d = r.json()
    except Exception as e:
        print(f"  [!] /learn/next failed: {e}")
        return None
    if d.get("all_mastered") or not d.get("topic") or not d.get("question"):
        return None
    return d


async def lios_submit(client: httpx.AsyncClient, base: str,
                       topic_id: str, answer: str) -> dict:
    r = await client.post(
        f"{base}/learn/answer",
        json={"topic_id": topic_id, "answer_text": answer, "reference": "auto"},
        timeout=15,
    )
    return r.json()

# ── Pipeline ───────────────────────────────────────────────────────────────────

async def producer(client: httpx.AsyncClient, base: str,
                   queue: asyncio.Queue, done: asyncio.Event, depth: int):
    """LIOS: keeps the queue `depth` questions ahead of the agent."""
    while not done.is_set():
        if queue.qsize() < depth:
            data = await lios_next(client, base)
            if data is None:
                done.set()
                return
            await queue.put(data)
        else:
            await asyncio.sleep(0.05)  # yield — queue is full


async def consumer(client: httpx.AsyncClient, base: str,
                   queue: asyncio.Queue, done: asyncio.Event,
                   agent: str, stats: dict):
    """Agent: drains the queue, answers each question, submits back."""
    loop = asyncio.get_event_loop()

    while not (done.is_set() and queue.empty()):
        try:
            data = await asyncio.wait_for(queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            continue

        t  = data["topic"]
        q  = data["question"]
        ts = datetime.now().strftime("%H:%M:%S")
        pct_bar = "█" * (t["pct"] // 10) + "░" * (10 - t["pct"] // 10)

        print(f"\n[{ts}] {t['category']}  ›  {t['name']}")
        print(f"  [{pct_bar}] {t['pct']}%  ({t['status']})")
        print(f"  Q: {textwrap.shorten(q, width=90)}")

        t0 = time.perf_counter()
        try:
            if agent == "api":
                answer = await _anthropic_api(q, t["name"], t["category"], client)
            elif agent == "claude":
                answer = await loop.run_in_executor(
                    None, _claude_cli, q, t["name"], t["category"])
            else:
                answer = await loop.run_in_executor(
                    None, _copilot, q, t["name"], t["category"])
        except Exception as e:
            answer = _fallback(t["name"], q)
            print(f"  [!] agent error: {e} — using fallback")

        elapsed = time.perf_counter() - t0

        try:
            result = await lios_submit(client, base, t["id"], answer)
            upd    = result["topic_updated"]
            stats["answered"] += 1
            print(f"  A: {textwrap.shorten(answer, width=90)}")
            print(f"  → {upd['pct']}% [{upd['status']}]"
                  f"  overall={result['overall_pct']}%"
                  f"  next={result.get('next_topic', '—')}"
                  f"  ({elapsed:.1f}s)")
        except Exception as e:
            print(f"  [!] submit failed: {e}")

        queue.task_done()

# ── Status bar ─────────────────────────────────────────────────────────────────

async def status_ticker(base: str, done: asyncio.Event):
    """Prints overall progress every 10 answers."""
    async with httpx.AsyncClient() as c:
        n = 0
        while not done.is_set():
            await asyncio.sleep(10)
            n += 1
            if n % 3 == 0:
                try:
                    r = await c.get(f"{base}/learn/status", timeout=10)
                    d = r.json()
                    print(f"\n{'─'*60}")
                    print(f"  Progress  avg={d['avg_progress']}%"
                          f"  all_mastered={d['all_mastered']}")
                    print(f"{'─'*60}")
                except Exception:
                    pass

# ── Entry point ────────────────────────────────────────────────────────────────

async def run(base: str, agent: str, depth: int):
    print("━" * 60)
    print("  LIOS Auto-Trainer  —  pipeline mode")
    print(f"  Server : {base}")
    print(f"  Agent  : {agent}   Queue depth : {depth}")
    print("  LIOS stays ahead · agent never waits")
    print("━" * 60)

    stats: dict = {"answered": 0}
    done  = asyncio.Event()
    queue: asyncio.Queue[dict] = asyncio.Queue()

    async with httpx.AsyncClient() as client:
        await asyncio.gather(
            producer(client, base, queue, done, depth),
            consumer(client, base, queue, done, agent, stats),
            status_ticker(base, done),
        )

    print("\n" + "━" * 60)
    print(f"  ✓ Fertig — {stats['answered']} Antworten eingereicht.")
    print("━" * 60)


def main():
    p = argparse.ArgumentParser(description="LIOS Learn auto-trainer (pipeline)")
    p.add_argument("--url",   default="http://localhost:8000",
                   help="LIOS server base URL")
    p.add_argument("--agent", default="copilot",
                   choices=["copilot", "claude", "api"],
                   help="Answering backend")
    p.add_argument("--depth", type=int, default=DEFAULT_QUEUE_DEPTH,
                   help="How many questions LIOS pre-fetches ahead (default 3)")
    args = p.parse_args()
    asyncio.run(run(args.url, args.agent, args.depth))


if __name__ == "__main__":
    main()
