"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lios import __version__
from lios.api.middleware.error_handler import global_exception_handler
from lios.api.routes import compliance, health, knowledge_base
from lios.database.connection import init_db
from lios.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LIOS v%s starting up…", __version__)
    await init_db()
    yield
    logger.info("LIOS shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="LIOS – Legal Intelligence Operating System",
        description=(
            "AI-powered EU sustainability compliance engine. "
            "Zero hallucination via three-agent consensus."
        ),
        version=__version__,
        lifespan=lifespan,
    )

    # ── CORS (allow all origins in dev; restrict in production) ───────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception handler ─────────────────────────────────────────────────────
    app.add_exception_handler(Exception, global_exception_handler)

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(compliance.router)
    app.include_router(knowledge_base.router)

    return app


app = create_app()
