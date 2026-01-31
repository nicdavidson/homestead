"""Config and agent identity endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Body

from ..config import settings, save_config_overrides, EDITABLE_FIELDS

router = APIRouter(prefix="/api", tags=["config"])

# ---------------------------------------------------------------------------
# Agent registry (mirrors common.models.AGENTS — self-contained)
# ---------------------------------------------------------------------------

AGENTS = {
    "herald": {
        "name": "herald",
        "display_name": "Herald",
        "emoji": "\U0001f4ef",
        "model_tier": "claude-cli",
    },
    "nightshift": {
        "name": "nightshift",
        "display_name": "Nightshift",
        "emoji": "\U0001f319",
        "model_tier": "sonnet",
    },
    "researcher": {
        "name": "researcher",
        "display_name": "Research",
        "emoji": "\U0001f50d",
        "model_tier": "grok",
    },
    "steward": {
        "name": "steward",
        "display_name": "Steward",
        "emoji": "\U0001f4cb",
        "model_tier": "sonnet",
    },
    "hearth": {
        "name": "hearth",
        "display_name": "Hearth",
        "emoji": "\U0001f3e0",
        "model_tier": "sonnet",
    },
}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/config")
def get_config():
    """Return current configuration (secrets redacted)."""
    return {
        "homestead_data_dir": settings.homestead_data_dir,
        "herald_data_dir": settings.herald_data_dir,
        "lore_dir": settings.lore_dir,
        "claude_cli_path": settings.claude_cli_path,
        "allowed_origins": settings.allowed_origins,
        "claude_timeout_s": settings.claude_timeout_s,
        "max_turns": settings.max_turns,
        "port": settings.port,
        "watchtower_db": str(settings.watchtower_db),
        "outbox_db": str(settings.outbox_db),
        "sessions_db": str(settings.sessions_db),
        "skills_dir": str(settings.skills_dir),
        "scratchpad_dir": str(settings.scratchpad_dir),
        "allowed_models": settings.allowed_models,
        "subagent_model": settings.subagent_model,
    }


@router.put("/config")
def update_config(updates: dict = Body(...)):
    """Update editable configuration values. Saves to overrides file with rolling backup."""
    # Filter to only editable keys
    filtered = {k: v for k, v in updates.items() if k in EDITABLE_FIELDS}
    if not filtered:
        return {"status": "no_changes", "editable_fields": list(EDITABLE_FIELDS.keys())}
    saved = save_config_overrides(filtered)
    return {"status": "ok", "saved": saved}


@router.get("/agents")
def list_agents():
    """List all agent identities from the registry."""
    return list(AGENTS.values())
