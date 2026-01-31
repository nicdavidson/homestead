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
    chat,
    config_routes,
    events,
    health,
    jobs,
    logs,
    lore,
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
