import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    allowed_user_ids: list[int]
    data_dir: str = "./data"
    claude_timeout_s: float = 300.0
    streaming_interval_s: float = 1.5
    max_queue_size: int = 5
    session_inactivity_hours: float = 4.0
    system_prompt: str = "You are a helpful personal AI assistant. Be concise and direct."
    claude_cli_path: str = "claude"
    max_turns: int = 5
    # Multi-model
    xai_api_key: str = ""
    anthropic_api_key: str = ""
    model_allowlist: list[str] = field(default_factory=lambda: ["claude", "sonnet", "opus", "grok"])
    subagent_models: list[str] = field(default_factory=lambda: ["grok", "sonnet"])
    # Shared infra
    homestead_data_dir: str = "~/.homestead"
    lore_dir: str = ""  # resolved at load time
    mcp_config_path: str = ""  # resolved at load time
    outbox_poll_interval_s: float = 2.0
    agent_name: str = "Milo"


def load_config() -> Config:
    load_dotenv()

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

    raw_ids = os.environ.get("ALLOWED_USER_IDS", "")
    if not raw_ids:
        raise RuntimeError("ALLOWED_USER_IDS is required")
    allowed_ids = [int(uid.strip()) for uid in raw_ids.split(",")]

    homestead_dir = os.environ.get("HOMESTEAD_DATA_DIR", "~/.homestead")
    lore_dir = os.environ.get("LORE_DIR", "")
    if not lore_dir:
        # Try to find lore/ relative to the package
        candidate = Path(__file__).resolve().parent.parent.parent.parent / "lore"
        if candidate.is_dir():
            lore_dir = str(candidate)

    # MCP config — auto-discover from monorepo
    mcp_config = os.environ.get("MCP_CONFIG_PATH", "")
    if not mcp_config:
        candidate = Path(__file__).resolve().parent.parent.parent.parent / "manor" / "mcp-config.json"
        if candidate.is_file():
            mcp_config = str(candidate)

    model_allowlist_raw = os.environ.get("MODEL_ALLOWLIST", "claude,sonnet,opus,grok")
    subagent_models_raw = os.environ.get("SUBAGENT_MODELS", "grok,sonnet")

    return Config(
        telegram_bot_token=token,
        allowed_user_ids=allowed_ids,
        data_dir=os.environ.get("DATA_DIR", "./data"),
        claude_timeout_s=float(os.environ.get("CLAUDE_TIMEOUT_S", "300")),
        streaming_interval_s=float(os.environ.get("STREAMING_INTERVAL_S", "1.5")),
        max_queue_size=int(os.environ.get("MAX_QUEUE_SIZE", "5")),
        session_inactivity_hours=float(os.environ.get("SESSION_INACTIVITY_HOURS", "4")),
        system_prompt=os.environ.get(
            "SYSTEM_PROMPT",
            "You are a helpful personal AI assistant. Be concise and direct.",
        ),
        claude_cli_path=os.environ.get("CLAUDE_CLI_PATH", "claude"),
        max_turns=int(os.environ.get("MAX_TURNS", "5")),
        xai_api_key=os.environ.get("XAI_API_KEY", ""),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        model_allowlist=[m.strip() for m in model_allowlist_raw.split(",") if m.strip()],
        subagent_models=[m.strip() for m in subagent_models_raw.split(",") if m.strip()],
        homestead_data_dir=homestead_dir,
        lore_dir=lore_dir,
        mcp_config_path=mcp_config,
        outbox_poll_interval_s=float(os.environ.get("OUTBOX_POLL_INTERVAL_S", "2.0")),
        agent_name=os.environ.get("AGENT_NAME", "Milo"),
    )
