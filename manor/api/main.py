"""Manor API — FastAPI backend for the Homestead dashboard.

Gateway between the Next.js frontend and the shared Homestead infrastructure
(SQLite databases, skill files, lore, scratchpad).

Run with:
    uvicorn manor.api.main:app --port 8700 --reload
or:
    python -m manor.api.main
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import (
    alerts,
    backup,
    chat,
    config_routes,
    events,
    health,
    jobs,
    journal,
    logs,
    lore,
    memory,
    outbox,
    proposals,
    scratchpad,
    sessions,
    skills,
    tasks,
    usage,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("manor.api")


def _init_watchtower() -> None:
    """Wire Manor API logs into the shared Watchtower database."""
    try:
        import sys
        from pathlib import Path

        common_pkg = str(Path(__file__).resolve().parent.parent.parent / "packages" / "common")
        if common_pkg not in sys.path:
            sys.path.insert(0, common_pkg)

        from common.watchtower import Watchtower, WatchtowerHandler

        wt = Watchtower(str(settings.watchtower_db))
        handler = WatchtowerHandler(wt, source="manor")
        handler.setLevel(logging.WARNING)  # Only WARNING+ to avoid flooding
        logging.getLogger().addHandler(handler)
        log.info("Watchtower logging enabled (%s)", settings.watchtower_db)
    except ImportError:
        log.debug("common package not available, Watchtower disabled")
    except Exception:
        log.warning("Failed to initialize Watchtower", exc_info=True)


_init_watchtower()

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Manor API",
    description="Homestead dashboard backend — serves the Next.js frontend.",
    version="0.1.0",
)

# -- CORS ------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- Routers ---------------------------------------------------------------

app.include_router(sessions.router)
app.include_router(logs.router)
app.include_router(skills.router)
app.include_router(lore.router)
app.include_router(scratchpad.router)
app.include_router(config_routes.router)
app.include_router(chat.router)
app.include_router(tasks.router)
app.include_router(jobs.router)
app.include_router(events.router)
app.include_router(outbox.router)
app.include_router(health.router)
app.include_router(usage.router)
app.include_router(proposals.router)
app.include_router(memory.router)
app.include_router(journal.router)
app.include_router(alerts.router)
app.include_router(backup.router)


# -- Startup: bootstrap Cronicle memory index ------------------------------

@app.on_event("startup")
async def _startup_reindex():
    """Bootstrap the Cronicle memory index on API start."""
    try:
        from .memory import get_memory_index
        idx = get_memory_index()
        idx.reindex_all()
    except Exception:
        log.exception("Cronicle startup reindex failed")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    log.info("Starting Manor API on port %s", settings.port)
    uvicorn.run(
        "manor.api.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=True,
    )
