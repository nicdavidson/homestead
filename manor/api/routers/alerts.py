"""Alert rules and history endpoints — manages Watchtower alert configuration."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

# ---------------------------------------------------------------------------
# Alert engine lazy init
# ---------------------------------------------------------------------------

_engine = None


def _get_engine():
    global _engine
    if _engine is not None:
        return _engine

    common_pkg = str(Path(__file__).resolve().parent.parent.parent.parent / "packages" / "common")
    if common_pkg not in sys.path:
        sys.path.insert(0, common_pkg)

    from common.alerts import AlertEngine

    hd = Path(settings.homestead_data_dir).expanduser()
    _engine = AlertEngine(
        alerts_db=hd / "alerts.db",
        watchtower_db=settings.watchtower_db,
        outbox_db=settings.outbox_db,
        chat_id=6038780843,  # TODO: make configurable
    )
    return _engine


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class RuleBody(BaseModel):
    id: str
    name: str
    description: str = ""
    rule_type: str
    config: dict[str, Any] = {}
    enabled: bool = True
    cooldown_s: int = 900


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/rules")
def list_rules():
    """List all alert rules."""
    engine = _get_engine()
    rules = engine.list_rules()
    return [
        {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "rule_type": r.rule_type,
            "config": r.config,
            "enabled": r.enabled,
            "cooldown_s": r.cooldown_s,
            "created_at": r.created_at,
        }
        for r in rules
    ]


@router.get("/rules/{rule_id}")
def get_rule(rule_id: str):
    """Get a single alert rule."""
    engine = _get_engine()
    rule = engine.get_rule(rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {
        "id": rule.id,
        "name": rule.name,
        "description": rule.description,
        "rule_type": rule.rule_type,
        "config": rule.config,
        "enabled": rule.enabled,
        "cooldown_s": rule.cooldown_s,
        "created_at": rule.created_at,
    }


@router.put("/rules")
def upsert_rule(body: RuleBody):
    """Create or update an alert rule."""
    engine = _get_engine()
    engine.upsert_rule({
        "id": body.id,
        "name": body.name,
        "description": body.description,
        "rule_type": body.rule_type,
        "config": body.config,
        "enabled": body.enabled,
        "cooldown_s": body.cooldown_s,
        "created_at": time.time(),
    })
    return {"status": "ok", "id": body.id}


@router.put("/rules/{rule_id}/toggle")
def toggle_rule(rule_id: str):
    """Toggle a rule enabled/disabled."""
    engine = _get_engine()
    if not engine.toggle_rule(rule_id):
        raise HTTPException(status_code=404, detail="Rule not found")
    rule = engine.get_rule(rule_id)
    return {"id": rule_id, "enabled": rule.enabled if rule else False}


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: str):
    """Delete an alert rule."""
    engine = _get_engine()
    if not engine.delete_rule(rule_id):
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"deleted": True, "id": rule_id}


@router.get("/history")
def list_history(limit: int = 50):
    """List recent alert events."""
    engine = _get_engine()
    events = engine.list_history(limit=limit)
    return [
        {
            "id": e.id,
            "rule_id": e.rule_id,
            "fired_at": e.fired_at,
            "message": e.message,
            "resolved": e.resolved,
            "resolved_at": e.resolved_at,
        }
        for e in events
    ]


@router.post("/check")
def run_check():
    """Manually trigger an alert check now."""
    engine = _get_engine()
    fired = engine.check_all()
    return {"checked": True, "alerts_fired": len(fired), "messages": fired}
