"""Dashboard UI route."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def _read_template(name: str) -> str:
    path = _TEMPLATE_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"<html><body><p>Template '{name}' not found.</p></body></html>"


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard() -> str:
    """Serve the LIOS sustainability dashboard."""
    return _read_template("dashboard.html")
