"""Manor API configuration — loaded from environment / .env file."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Fields that can be changed at runtime via the UI.
EDITABLE_FIELDS: dict[str, type] = {
    "allowed_models": list,
    "subagent_model": str,
    "max_turns": int,
    "claude_timeout_s": float,
    "allowed_origins": list,
}


@dataclass
class Settings:
    homestead_data_dir: str
    herald_data_dir: str
    lore_dir: str
    claude_cli_path: str
    allowed_origins: list[str]
    claude_timeout_s: float = 300.0
    max_turns: int = 10
    port: int = 8700
    allowed_models: list[str] = field(default_factory=lambda: [
        "sonnet", "haiku", "claude-sonnet-4-20250514",
        "claude-haiku-4-20250414",
    ])
    subagent_model: str = "sonnet"  # default model for MCP sub-agents

    # -- derived paths ---------------------------------------------------------

    @property
    def watchtower_db(self) -> Path:
        return Path(self.homestead_data_dir).expanduser() / "watchtower.db"

    @property
    def outbox_db(self) -> Path:
        return Path(self.homestead_data_dir).expanduser() / "outbox.db"

    @property
    def sessions_db(self) -> Path:
        return Path(self.herald_data_dir).expanduser() / "sessions.db"

    @property
    def skills_dir(self) -> Path:
        return Path(self.homestead_data_dir).expanduser() / "skills"

    @property
    def scratchpad_dir(self) -> Path:
        return Path(self.homestead_data_dir).expanduser() / "scratchpad"

    @property
    def usage_db(self) -> Path:
        return Path(self.homestead_data_dir).expanduser() / "usage.db"

    @property
    def proposals_db(self) -> Path:
        return Path(self.homestead_data_dir).expanduser() / "proposals.db"

    @property
    def lore_path(self) -> Path:
        return Path(self.lore_dir).expanduser()


def _overrides_path(data_dir: str = "~/.homestead") -> Path:
    return Path(data_dir).expanduser() / "config_overrides.json"


def _load_overrides(data_dir: str = "~/.homestead") -> dict:
    p = _overrides_path(data_dir)
    if p.is_file():
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


MAX_BACKUPS = 10


def _rotate_backups(p: Path) -> None:
    """Keep up to MAX_BACKUPS rolling copies of the config file."""
    backup_dir = p.parent / "config_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    if p.is_file():
        import time
        ts = time.strftime("%Y%m%d_%H%M%S")
        dest = backup_dir / f"config_overrides.{ts}.json"
        dest.write_text(p.read_text())

        # Prune old backups
        backups = sorted(backup_dir.glob("config_overrides.*.json"))
        while len(backups) > MAX_BACKUPS:
            backups.pop(0).unlink()


def save_config_overrides(updates: dict) -> dict:
    """Merge *updates* into the overrides file and reload settings."""
    p = _overrides_path(settings.homestead_data_dir)
    existing = _load_overrides(settings.homestead_data_dir)

    # Rolling backup before writing
    _rotate_backups(p)

    for key, value in updates.items():
        if key not in EDITABLE_FIELDS:
            continue
        expected = EDITABLE_FIELDS[key]
        if expected is list and isinstance(value, str):
            value = [v.strip() for v in value.split(",") if v.strip()]
        existing[key] = value

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(existing, indent=2))

    # Apply to the live singleton
    for key, value in existing.items():
        if hasattr(settings, key):
            setattr(settings, key, value)

    return existing


def load_settings() -> Settings:
    """Build a Settings instance from environment variables / .env."""
    load_dotenv()

    homestead_dir = os.environ.get("HOMESTEAD_DATA_DIR", "~/.homestead")

    # Herald data dir — try env, then common sibling path
    herald_data_dir = os.environ.get("HERALD_DATA_DIR", "")
    if not herald_data_dir:
        candidate = (
            Path(__file__).resolve().parent.parent.parent
            / "packages"
            / "herald"
            / "data"
        )
        if candidate.is_dir():
            herald_data_dir = str(candidate)
        else:
            herald_data_dir = str(
                Path(homestead_dir).expanduser() / "herald"
            )

    # Lore directory
    lore_dir = os.environ.get("LORE_DIR", "")
    if not lore_dir:
        candidate = Path(__file__).resolve().parent.parent.parent / "lore"
        if candidate.is_dir():
            lore_dir = str(candidate)
        else:
            lore_dir = str(Path(homestead_dir).expanduser() / "lore")

    origins_raw = os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:3001,http://localhost:3002",
    )
    allowed_origins = [o.strip() for o in origins_raw.split(",") if o.strip()]

    # Allowed models — comma-separated list, or defaults
    allowed_models_raw = os.environ.get("ALLOWED_MODELS", "")
    allowed_models = (
        [m.strip() for m in allowed_models_raw.split(",") if m.strip()]
        if allowed_models_raw
        else ["sonnet", "haiku", "claude-sonnet-4-20250514", "claude-haiku-4-20250414"]
    )

    s = Settings(
        homestead_data_dir=homestead_dir,
        herald_data_dir=herald_data_dir,
        lore_dir=lore_dir,
        claude_cli_path=os.environ.get("CLAUDE_CLI_PATH", "claude"),
        allowed_origins=allowed_origins,
        claude_timeout_s=float(os.environ.get("CLAUDE_TIMEOUT_S", "300")),
        max_turns=int(os.environ.get("MAX_TURNS", "10")),
        port=int(os.environ.get("MANOR_PORT", "8700")),
        allowed_models=allowed_models,
        subagent_model=os.environ.get("SUBAGENT_MODEL", "sonnet"),
    )

    # Apply any saved overrides from the UI
    overrides = _load_overrides(homestead_dir)
    for key, value in overrides.items():
        if hasattr(s, key) and key in EDITABLE_FIELDS:
            setattr(s, key, value)

    return s


# Singleton — importable from anywhere in the API
settings = load_settings()
