#!/usr/bin/env python3
"""
LIOS Learn Copilot
==================
An autonomous terminal agent that teaches LIOS by answering its own learn-mode
questions using LIOS's own knowledge corpus (self-reinforcing loop).

Usage
-----
    # Fully autonomous — runs until all topics mastered or --rounds limit
    python3 scripts/learn_copilot.py --mode auto

    # Interactive — shows each question, waits for Enter before submitting
    python3 scripts/learn_copilot.py --mode interactive

    # Review mode — only prints questions without answering (useful for studying)
    python3 scripts/learn_copilot.py --mode review --rounds 10

    # Custom server
    python3 scripts/learn_copilot.py --server http://192.168.1.42:8000

Options
-------
    --server URL        LIOS server base URL  [default: http://localhost:8000]
    --mode MODE         auto | interactive | review  [default: interactive]
    --rounds N          Max rounds to run (0 = unlimited)  [default: 20]
    --delay SECS        Seconds to wait between rounds  [default: 1.0]
    --min-answer CHARS  Minimum answer length to submit  [default: 60]
    --topic TOPIC_ID    Pin to a specific topic ID
"""

from __future__ import annotations

import argparse
import sys
import time
import textwrap
from typing import Any

try:
    import requests
except ImportError:
    print("ERROR: requests is not installed.  Run:  pip install requests", file=sys.stderr)
    sys.exit(1)

# ── ANSI colour helpers (no deps) ──────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"

GREEN  = "\033[32m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
RED    = "\033[31m"
BLUE   = "\033[34m"
MAGENTA= "\033[35m"
WHITE  = "\033[97m"

BG_DARK = "\033[48;5;234m"   # dark bg for quotes

def _c(color: str, text: str) -> str:
    return f"{color}{text}{RESET}"

def _bar(pct: int, width: int = 32) -> str:
    filled = int(width * pct / 100)
    color  = GREEN if pct >= 80 else YELLOW if pct >= 40 else RED
    bar    = "█" * filled + "░" * (width - filled)
    return f"{color}{bar}{RESET} {BOLD}{pct}%{RESET}"

def _wrap(text: str, indent: int = 4) -> str:
    prefix = " " * indent
    return textwrap.fill(text, width=80, initial_indent=prefix, subsequent_indent=prefix)

# ── HTTP helpers ───────────────────────────────────────────────────────────────

class LIOSClient:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base   = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def _get(self, path: str, **params: Any) -> dict:
        r = self.session.get(f"{self.base}{path}", params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, body: dict) -> dict:
        r = self.session.post(f"{self.base}{path}", json=body, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def learn_next(self, topic_id: str | None = None) -> dict:
        params = {"topic_id": topic_id} if topic_id else {}
        return self._get("/learn/next", **params)

    def learn_answer(self, topic_id: str, answer: str, reference: str = "") -> dict:
        return self._post("/learn/answer", {
            "topic_id": topic_id,
            "answer_text": answer,
            "reference": reference,
        })

    def learn_map(self) -> dict:
        return self._get("/learn/map")

    def synthesize(self, question: str) -> dict:
        return self._post("/synthesize", {"query": question})

    def ping(self) -> bool:
        try:
            self._get("/health")
            return True
        except Exception:
            return False

# ── Answer generation ──────────────────────────────────────────────────────────

def _generate_answer(client: LIOSClient, question: str, topic_name: str, min_len: int) -> str | None:
    """Ask LIOS to synthesize an answer for the given question using its own corpus."""
    # We frame it as a legal question to get a knowledge-grounded response
    query = f"{question} (context: {topic_name} in EU legal compliance)"
    try:
        result = client.synthesize(query)
        answer = result.get("answer", "").strip()
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            # /synthesize not available, fall back to /query
            try:
                result = client._post("/query", {"query": query})
                answer = result.get("answer", "").strip()
            except Exception:
                return None
        else:
            return None
    except Exception:
        return None

    if not answer or len(answer) < min_len:
        return None
    return answer

# ── Display helpers ────────────────────────────────────────────────────────────

def _header():
    print()
    print(_c(CYAN + BOLD, "  ┌─────────────────────────────────────────────────┐"))
    print(_c(CYAN + BOLD, "  │       LIOS Learn Copilot  ·  自習モード         │"))
    print(_c(CYAN + BOLD, "  └─────────────────────────────────────────────────┘"))
    print()

def _print_map_summary(map_data: dict):
    overall = map_data.get("overall_pct", 0)
    mastered  = map_data.get("mastered", 0)
    functional= map_data.get("functional", 0)
    learning  = map_data.get("learning", 0)
    unknown   = map_data.get("unknown", 0)
    print(f"  {_c(BOLD, 'Knowledge Map')}  {_bar(overall, 28)}")
    print(
        f"  {_c(GREEN, f'✓ {mastered+functional} known')}  "
        f"{_c(YELLOW, f'◎ {learning} learning')}  "
        f"{_c(DIM, f'○ {unknown} unknown')}"
    )
    print()

def _print_round(n: int, total: int | None):
    label = f"Round {n}" + (f" / {total}" if total else "")
    print(_c(DIM, f"  {'─'*50}"))
    print(_c(BOLD + MAGENTA, f"  {label}"))

def _print_topic(topic: dict):
    status_icon = {
        "mastered": "🏆", "functional": "✅", "connected": "🧩",
        "learning": "📖", "seed": "🌱", "unknown": "🔲",
    }.get(topic.get("status", "unknown"), "🔲")
    name     = topic.get("name", "?")
    category = topic.get("category", "")
    pct      = topic.get("pct", 0)
    status   = topic.get("status", "?")
    print(f"\n  {status_icon}  {_c(BOLD + WHITE, name)}  {_c(DIM, f'[{category}]')}")
    print(f"     {_bar(pct, 20)}  {_c(DIM, status)}")
    print()

def _print_question(question: str, qtype: str | None):
    label = f"  QUESTION  [{qtype or 'unknown'}]"
    print(_c(YELLOW + BOLD, label))
    print(_c(YELLOW, "  " + "─" * 46))
    for line in question.split("\n"):
        print(_c(YELLOW, _wrap(line.strip(), indent=4)))
    print()

def _print_answer(answer: str, generated: bool = True):
    src = _c(CYAN, "LIOS corpus") if generated else _c(GREEN, "you")
    print(_c(BOLD, f"  ANSWER  ← {src}"))
    print(_c(DIM, "  " + "─" * 46))
    preview = answer[:600] + ("…" if len(answer) > 600 else "")
    for line in preview.split("\n"):
        print(_wrap(line, indent=4))
    print()

def _print_result(result: dict):
    tu = result.get("topic_updated", {})
    name   = tu.get("name", "?")
    pct    = tu.get("pct", 0)
    status = tu.get("status", "?")
    overall= result.get("overall_pct", 0)
    next_t = result.get("next_topic")

    print(_c(GREEN + BOLD, f"  ✓ Submitted  →  {name}: {pct}% ({status})"))
    print(f"  Overall: {_bar(overall, 24)}")
    if next_t:
        print(f"  Up next: {_c(CYAN, next_t)}")
    print()

# ── Main loop ─────────────────────────────────────────────────────────────────

def run(args: argparse.Namespace):
    client   = LIOSClient(args.server)
    mode     = args.mode
    max_rounds = args.rounds  # 0 = unlimited
    delay    = args.delay
    min_len  = args.min_answer
    pin_topic = args.topic

    _header()

    # Connectivity check
    print(_c(DIM, f"  Connecting to {args.server} …"), end="", flush=True)
    if not client.ping():
        print(_c(RED, " FAILED"))
        print(_c(RED, "\n  Server not reachable. Start LIOS with:"))
        print(_c(WHITE, "    uvicorn lios_server:app --host 0.0.0.0 --port 8000"))
        sys.exit(1)
    print(_c(GREEN, " OK"))
    print()

    # Initial map snapshot
    try:
        map_data = client.learn_map()
        _print_map_summary(map_data)
    except Exception:
        pass

    round_num = 0
    submitted = 0
    skipped   = 0

    while True:
        round_num += 1
        if max_rounds and round_num > max_rounds:
            break

        _print_round(round_num, max_rounds if max_rounds else None)

        # 1. Get next question
        try:
            data = client.learn_next(topic_id=pin_topic)
        except Exception as exc:
            print(_c(RED, f"  ERROR fetching question: {exc}"))
            break

        if data.get("all_mastered"):
            print(_c(GREEN + BOLD, "\n  🏆  All topics mastered! LIOS has learned everything.\n"))
            break

        topic    = data.get("topic") or {}
        question = data.get("question") or ""
        qtype    = data.get("question_type")

        if not question or not topic:
            print(_c(RED, "  No question received — stopping."))
            break

        _print_topic(topic)
        _print_question(question, qtype)

        if mode == "review":
            print(_c(DIM, "  [review mode — not submitting]\n"))
            if max_rounds and round_num >= max_rounds:
                break
            if delay:
                time.sleep(delay)
            continue

        # 2. Generate answer
        if mode == "interactive":
            print(_c(DIM, "  Generating answer from corpus…"), end="", flush=True)

        answer = _generate_answer(client, question, topic.get("name", ""), min_len)

        if mode == "interactive":
            print(_c(GREEN, " done") if answer else _c(RED, " failed"))
            print()

        if not answer:
            print(_c(YELLOW, "  Could not generate a sufficient answer — skipping.\n"))
            skipped += 1
            if delay:
                time.sleep(delay)
            continue

        _print_answer(answer, generated=True)

        # 3. In interactive mode, ask for confirmation
        if mode == "interactive":
            try:
                choice = input(
                    _c(BOLD, "  Submit this answer? ")
                    + _c(DIM, "[Enter=yes  s=skip  e=edit  q=quit]: ")
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if choice == "q":
                break
            elif choice == "s":
                print(_c(DIM, "  Skipped.\n"))
                skipped += 1
                continue
            elif choice == "e":
                print(_c(DIM, "  Your answer (Ctrl+D when done):"))
                lines = []
                try:
                    while True:
                        lines.append(input("  "))
                except (EOFError, KeyboardInterrupt):
                    pass
                if lines:
                    answer = "\n".join(lines).strip()
                    if len(answer) < min_len:
                        print(_c(YELLOW, "  Answer too short — skipping.\n"))
                        skipped += 1
                        continue
                else:
                    print(_c(DIM, "  No input — skipping.\n"))
                    skipped += 1
                    continue

        # 4. Submit answer
        try:
            result = client.learn_answer(
                topic_id=topic["id"],
                answer=answer,
                reference="LIOS corpus (auto-synthesized)",
            )
            _print_result(result)
            submitted += 1
        except Exception as exc:
            print(_c(RED, f"  Submit failed: {exc}\n"))
            skipped += 1

        if delay and round_num < (max_rounds or round_num + 1):
            time.sleep(delay)

    # Summary
    print(_c(DIM, "  " + "─" * 50))
    print(_c(BOLD, f"  Session complete  —  {submitted} submitted, {skipped} skipped"))
    try:
        map_data = client.learn_map()
        _print_map_summary(map_data)
    except Exception:
        pass

# ── CLI ────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="learn_copilot",
        description="LIOS Learn Copilot — teaches LIOS using its own corpus in terminal mode.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--server",     default="http://localhost:8000",
                   help="LIOS server URL  [default: http://localhost:8000]")
    p.add_argument("--mode",       choices=["auto", "interactive", "review"],
                   default="interactive",
                   help="auto=fully autonomous  interactive=confirm each  review=read only")
    p.add_argument("--rounds",     type=int, default=20,
                   help="Max rounds to run (0=unlimited)  [default: 20]")
    p.add_argument("--delay",      type=float, default=1.0,
                   help="Seconds between rounds  [default: 1.0]")
    p.add_argument("--min-answer", type=int, default=60, dest="min_answer",
                   help="Min answer length to submit  [default: 60]")
    p.add_argument("--topic",      default=None,
                   help="Pin to a specific topic ID (optional)")
    return p

if __name__ == "__main__":
    try:
        run(_build_parser().parse_args())
    except KeyboardInterrupt:
        print(_c(DIM, "\n\n  Interrupted.\n"))
        sys.exit(0)
