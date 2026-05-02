"""AI activity tracking utilities.

Records AI-driven actions to `logs/ai_activity.jsonl` and optionally commits
them to git when `LIOS_AI_AUTO_COMMIT=true` is set in the environment.

Each record is a JSON object with timestamp, actor, action, description,
affected_files and optional git commit metadata.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


@dataclass
class AIActivity:
    timestamp: str
    actor: str
    action: str
    description: Optional[str]
    affected_files: list[str]
    metadata: dict


class AIActivityLogger:
    """Simple append-only AI activity logger.

    Writes JSONL entries to `logs/ai_activity.jsonl`. If the environment
    variable `LIOS_AI_AUTO_COMMIT` is set to "true", the logger will also
    run a `git add` and `git commit` with a short message containing actor
    and action.
    """

    def __init__(self, path: str | None = None) -> None:
        self.path = Path(path or "logs/ai_activity.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.auto_commit = os.getenv("LIOS_AI_AUTO_COMMIT", "false").lower() == "true"

    def log(
        self,
        actor: str,
        action: str,
        description: Optional[str] = None,
        affected_files: Optional[Iterable[str]] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        record = AIActivity(
            timestamp=now,
            actor=actor,
            action=action,
            description=description,
            affected_files=list(affected_files or []),
            metadata=metadata or {},
        )

        # Append to JSONL log
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

        # Optionally commit to git for audit trail
        if self.auto_commit and record.affected_files:
            try:
                # Stage files
                subprocess.run(["git", "add", "-A"], check=True)
                # Commit with a concise message
                msg = f"AI[{actor}]: {action}"
                subprocess.run(["git", "commit", "-m", msg], check=True)
            except Exception:
                # Do not raise; keep logging best-effort
                pass
