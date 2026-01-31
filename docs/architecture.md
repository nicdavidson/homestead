# Homestead Architecture

This document describes the internal architecture of Homestead: how the packages relate to each other, how data flows through the system, and how the individual components are structured.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Package Dependency Graph](#package-dependency-graph)
3. [Message Flow](#message-flow)
4. [Cross-Package Communication via Outbox](#cross-package-communication-via-outbox)
5. [Database Schema Reference](#database-schema-reference)
6. [Watchtower Logging Architecture](#watchtower-logging-architecture)
7. [Skills and Lore System](#skills-and-lore-system)
8. [Manor API Gateway Architecture](#manor-api-gateway-architecture)
9. [Configuration Cascade](#configuration-cascade)
10. [Data Directory Layout](#data-directory-layout)

---

## System Overview

Homestead is a personal AI infrastructure framework organized as a Python monorepo. The system has two primary user interfaces (Telegram and web), a shared infrastructure layer, and specialized service packages for task management and job scheduling.

```
                    User
                     |
          +----------+----------+
          |                     |
     Telegram App          Web Browser
          |                     |
          v                     v
    +-----+------+      +------+-------+
    |   Herald    |      |    Manor     |
    |  (aiogram)  |      | Next.js + FastAPI
    |  port: n/a  |      | ports: 3000, 8700
    +-----+------+      +------+-------+
          |                     |
          |   +-----------+    |
          +-->|  common   |<---+
          |   | watchtower|    |
          |   | outbox    |    |
          |   | skills    |    |
          |   | models    |    |
          |   | db        |    |
          |   +-----+-----+   |
          |         |          |
     +----+----+  +-+------+--+-----+
     | Claude  |  | steward| almanac|
     |   CLI   |  | tasks  |  jobs  |
     +---------+  +--------+--------+
          |
          v
    +-----+------+      +----------+
    | lore/      |      | hearth   |
    | soul.md    |      | agents   |
    | claude.md  |      | core     |
    | user.md    |      | services |
    | triggers.md|      +----------+
    +------------+

    Data at rest: ~/.homestead/
    +-----------------------------------------+
    | watchtower.db    Structured log store    |
    | outbox.db        Pending TG messages     |
    | steward/tasks.db Task management         |
    | almanac/jobs.db  Scheduled jobs          |
    | skills/          Markdown skill files    |
    | scratchpad/      Persistent AI memory    |
    +-----------------------------------------+
```

### Design Principles

- **SQLite for all persistence.** No external database servers. Every package stores state in SQLite with WAL mode.
- **Filesystem for content.** Skills, scratchpad notes, and lore files are plain markdown on disk.
- **Environment variables for configuration.** All settings flow through `.env` files loaded by `python-dotenv`.
- **Self-contained API routers.** Manor's FastAPI routers duplicate schema definitions rather than importing from package code, keeping the web layer decoupled.
- **Anti-sycophancy by design.** The AI's identity is defined in lore files that explicitly instruct against flattery and hedging.

---

## Package Dependency Graph

The arrows indicate "depends on" relationships. Runtime imports flow downward.

```
  herald --------+
     |           |
     v           |
  common <-------+------ manor (API)
     ^           |
     |           |
  steward -------+
     ^           |
     |           |
  almanac -------+
     ^
     |
  hearth (optional, uses common and integrations)
```

### Import Relationships

| Package | Imports from |
|---|---|
| `common` | Standard library only |
| `herald` | `common` (watchtower, outbox, models), `aiogram`, `httpx`, `python-dotenv` |
| `steward` | `common` (implicitly, via shared DB paths) |
| `almanac` | `common` (outbox for the "outbox" action type) |
| `hearth` | `common`, various AI provider SDKs |
| `manor` (API) | `fastapi`, `python-dotenv`; accesses `common` and `almanac` stores via SQLite directly |

A key architectural decision: **Manor's API routers access SQLite databases directly** rather than importing from Python packages. This means Manor can read Herald's session database, Steward's task database, and Almanac's job database without having those packages installed. Schema definitions are duplicated in each router file to maintain this independence.

---

## Message Flow

### Telegram Message Flow

The complete lifecycle of a user message through Telegram:

```
  User sends message in Telegram
         |
         v
  +------+--------+
  | Telegram API   |
  | (aiogram poll) |
  +------+--------+
         |
         v
  +------+--------+
  | AuthMiddleware |  <-- checks user_id against ALLOWED_USER_IDS
  +------+--------+
         |
         v
  +------+---------+
  | handle_message |  <-- F.text handler
  +------+---------+
         |
         v
  +------+--------+
  | MessageQueue   |  <-- per-chat FIFO queue (max 5 messages)
  +------+--------+
         |
         v
  +------+---------+
  | process_queue  |  <-- drains queue one message at a time
  +------+---------+
         |
         +------> SessionManager.get_active(chat_id)
         |              |
         |              +--> stale? --> rotate (new session)
         |              +--> None?  --> create (new session)
         |
         v
  +------+----------+
  | dispatch_message |  <-- routes to correct model backend
  +------+----------+
         |
         +---+--- model == "claude" | "sonnet" | "opus" ---+
         |                                                  |
         v                                                  v
  +------+--------+                                 +-------+------+
  | spawn_claude  |                                 | _call_xai    |
  | (CLI process) |                                 | (httpx REST) |
  +------+--------+                                 +-------+------+
         |                                                  |
         |  stream-json output                              | SSE stream
         |                                                  |
         +---->  on_delta callback  <-----------------------+
         |           |
         |           v
         |   Progressive Telegram
         |   message edits (every 1.5s)
         |
         v
  +------+--------+
  | Final result   |  <-- md_to_telegram_html conversion
  | sent/edited    |  <-- split_message for >4000 chars
  +---------------+
```

### Web Chat Flow (Manor)

```
  Browser opens WebSocket to ws://manor-api:8700/ws/chat
         |
         v
  +------+--------+
  | WebSocket      |
  | accept()       |
  +------+--------+
         |
         v  (receives JSON: {session_name, chat_id, message})
  +------+----------+
  | _get_or_create  |  <-- looks up or creates session in sessions.db
  |    _session     |
  +------+----------+
         |
         v
  +------+-----------+
  | _spawn_and_stream|  <-- spawns Claude CLI subprocess
  +------+-----------+
         |
         |  stream-json stdout
         |
         v
  +------+--------+
  | WebSocket      |  <-- sends {type: "delta", text: "..."}
  | send_json()    |  <-- sends {type: "result", text: "...", session_id: "..."}
  +------+--------+  <-- sends {type: "error", message: "..."} on failure
         |
         v
  +------+--------+
  | _update_session|  <-- bumps message_count, last_active_at
  | _after_response|
  +---------------+
```

---

## Cross-Package Communication via Outbox

The outbox is the mechanism for any package to send a Telegram message without having direct access to the Telegram bot. It uses a shared SQLite database as a message queue.

### How It Works

```
  Any package (almanac, steward, hearth, etc.)
         |
         v
  common.outbox.post_message()
         |
         v
  +------+--------+
  | outbox.db      |
  | status=pending |
  +------+--------+
         |
         v  (polled every 2 seconds by Herald)
  +------+--------+
  | poll_outbox()  |
  +------+--------+
         |
         v
  common.models.format_agent_message()
         |  adds agent emoji + bold name prefix
         v
  +------+--------+
  | bot.send_msg  |  <-- delivered to the target chat_id
  +------+--------+
         |
         v
  outbox.mark_sent(msg_id)
  or outbox.mark_failed(msg_id)
```

### Message Lifecycle

1. **Pending** -- inserted by any package via `post_message()`.
2. **Sent** -- Herald successfully delivered to Telegram.
3. **Failed** -- delivery failed (network error, invalid chat_id, etc.).

### Agent Identity Formatting

When a non-Herald agent sends through the outbox, the message is prefixed with the agent's identity:

```
[emoji] [Bold Agent Name]

Message body here...
```

Herald's own messages have no prefix. The agent registry is defined in `common/common/models.py`.

---

## Database Schema Reference

All databases use SQLite with WAL journal mode and a 5000ms busy timeout.

### watchtower.db (`~/.homestead/watchtower.db`)

Structured log store. Every significant event across the system is recorded here.

```sql
CREATE TABLE logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp  REAL    NOT NULL,        -- Unix timestamp (time.time())
    level      TEXT    NOT NULL,        -- DEBUG, INFO, WARNING, ERROR
    source     TEXT    NOT NULL,        -- e.g. "herald.bot", "almanac.scheduler"
    message    TEXT    NOT NULL,        -- Human-readable log message
    data_json  TEXT,                    -- Optional structured data (JSON)
    session_id TEXT,                    -- Optional session ID for context
    chat_id    INTEGER                  -- Optional Telegram chat ID
);

CREATE INDEX idx_logs_ts_level ON logs (timestamp, level);
```

### outbox.db (`~/.homestead/outbox.db`)

Cross-package message queue for Telegram delivery.

```sql
CREATE TABLE outbox (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id    INTEGER NOT NULL,        -- Target Telegram chat ID
    agent_name TEXT    NOT NULL,        -- e.g. "almanac", "steward", "hearth"
    message    TEXT    NOT NULL,        -- Message body (HTML or plain text)
    parse_mode TEXT    DEFAULT 'HTML',  -- Telegram parse mode
    created_at REAL    NOT NULL,        -- Unix timestamp
    sent_at    REAL,                    -- When Herald delivered it
    status     TEXT    DEFAULT 'pending' -- pending | sent | failed
);

CREATE INDEX idx_outbox_status ON outbox (status, created_at);
```

### sessions.db (`packages/herald/data/sessions.db`)

Herald's conversation session store. Manages multi-session, multi-model conversations.

```sql
CREATE TABLE sessions (
    chat_id           INTEGER NOT NULL,     -- Telegram chat ID
    name              TEXT    NOT NULL,     -- Session name (e.g. "default", "research")
    user_id           INTEGER NOT NULL,     -- Telegram user ID
    claude_session_id TEXT    NOT NULL,     -- Claude CLI session ID (UUID)
    model             TEXT    NOT NULL DEFAULT 'claude', -- claude | sonnet | opus | grok
    is_active         INTEGER NOT NULL DEFAULT 1,       -- Only one active per chat
    created_at        REAL    NOT NULL,     -- Unix timestamp
    last_active_at    REAL    NOT NULL,     -- Last message timestamp
    message_count     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (chat_id, name)
);
```

### tasks.db (`~/.homestead/steward/tasks.db`)

Steward's task management store.

```sql
CREATE TABLE tasks (
    id              TEXT PRIMARY KEY,       -- UUID
    title           TEXT NOT NULL,
    description     TEXT DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'pending',   -- pending | in_progress | blocked | completed | cancelled
    priority        TEXT NOT NULL DEFAULT 'normal',    -- low | normal | high | urgent
    assignee        TEXT DEFAULT 'auto',               -- auto | user | agent name
    blockers_json   TEXT DEFAULT '[]',                 -- JSON array of Blocker objects
    depends_on_json TEXT DEFAULT '[]',                 -- JSON array of task ID strings
    created_at      REAL NOT NULL,
    updated_at      REAL NOT NULL,
    completed_at    REAL,                              -- Set when status -> completed
    tags_json       TEXT DEFAULT '[]',                 -- JSON array of tag strings
    notes_json      TEXT DEFAULT '[]',                 -- JSON array of note strings
    source          TEXT DEFAULT ''                     -- Which module created the task
);

CREATE INDEX idx_tasks_status ON tasks (status);
CREATE INDEX idx_tasks_priority ON tasks (priority, status);
```

**Blocker JSON structure:**

```json
{
    "type": "human_input | human_approval | human_action | dependency",
    "description": "What is blocking this task",
    "created_at": 1700000000.0,
    "resolved_at": null,
    "resolved_by": null,
    "resolution": null
}
```

### jobs.db (`~/.homestead/almanac/jobs.db`)

Almanac's scheduled job store.

```sql
CREATE TABLE jobs (
    id                TEXT PRIMARY KEY,     -- UUID
    name              TEXT NOT NULL,
    description       TEXT DEFAULT '',
    schedule_type     TEXT NOT NULL,        -- cron | interval | once
    schedule_value    TEXT NOT NULL,        -- cron: "0 9 * * *", interval: seconds, once: ISO datetime
    action_type       TEXT NOT NULL,        -- outbox | command | webhook
    action_config_json TEXT NOT NULL,       -- JSON object with action-specific config
    enabled           INTEGER DEFAULT 1,
    last_run_at       REAL,
    next_run_at       REAL,
    run_count         INTEGER DEFAULT 0,
    created_at        REAL NOT NULL,
    tags_json         TEXT DEFAULT '[]',
    source            TEXT DEFAULT 'almanac'
);

CREATE INDEX idx_jobs_next_run ON jobs (enabled, next_run_at);
```

**Action config structures by action_type:**

```json
// outbox
{"chat_id": 12345, "agent_name": "almanac", "message": "Reminder: ..."}

// command
{"command": "/usr/bin/python3", "args": ["script.py"], "timeout": 60}

// webhook
{"url": "https://example.com/hook", "method": "POST", "headers": {}, "body": "{}"}
```

---

## Watchtower Logging Architecture

Watchtower is Homestead's structured logging system. It writes to a SQLite database so that logs are queryable by both humans (via the Manor log viewer or `sqlite3` CLI) and by the AI itself.

### Architecture

```
  +----------+     +----------+     +----------+
  |  herald  |     |  almanac |     |  any pkg |
  | (Python  |     | (Python  |     | (Python  |
  |  logger) |     |  logger) |     |  logger) |
  +----+-----+     +----+-----+     +----+-----+
       |                |                |
       v                v                v
  +----+----------------+----------------+-----+
  |           WatchtowerHandler                 |
  |    (stdlib logging.Handler subclass)        |
  +----+---+--------------------------------+--+
       |   |                                |
       v   v                                v
  +----+---+---+    query()     +-----------+--+
  | watchtower |<---------------|  Manor API   |
  |   .db      |  errors_since  |  /api/logs   |
  |            |  summary()     |              |
  +------------+                +--------------+
```

### How Packages Use Watchtower

Each package initializes a `WatchtowerHandler` with its own source name:

```python
from common.watchtower import Watchtower, WatchtowerHandler

wt = Watchtower("~/.homestead/watchtower.db")
handler = WatchtowerHandler(wt, source="herald")
logging.getLogger().addHandler(handler)
```

From that point on, all standard Python `logging` calls from that package are automatically persisted to SQLite with the source prefix.

### Query API

The `Watchtower` class provides three read methods:

- **`query(since, until, level, source, search, limit)`** -- flexible filtered queries.
- **`errors_since(hours)`** -- convenience method for recent errors.
- **`summary(hours)`** -- grouped counts by source and level.

These are used by Herald's `/logs` command and Manor's log viewer.

---

## Skills and Lore System

### Lore (Identity Layer)

Lore files define the AI's identity and behavior. They live in the `lore/` directory at the repository root and are assembled into the system prompt at runtime.

| File | Purpose | Loaded |
|---|---|---|
| `soul.md` | Core entity identity, principles, values | First |
| `claude.md` | Behavioral directives: tone, anti-sycophancy, response style | Second |
| `user.md` | User context and preferences (gitignored) | Third |
| `triggers.md` | Proactive behavior triggers | As extra lore |
| `*.md` (others) | Any additional lore files | Last |

**System prompt assembly order** (in `herald/herald/prompt.py`):

1. `soul.md` content
2. `claude.md` content
3. `user.md` content
4. Skills section (names + descriptions)
5. Scratchpad hint (lists available notes)
6. Any remaining `*.md` files in `lore/`

Sections are joined with `\n\n---\n\n` separators. If no lore files exist, the system falls back to the `SYSTEM_PROMPT` environment variable.

### Skills (Capability Layer)

Skills are markdown files stored at `~/.homestead/skills/`. Each skill describes a procedure or capability the AI can reference.

**File format:**

```markdown
---
name: git-workflow
description: Standard git commit and PR workflow
tags: git, workflow
---

When committing changes:
1. Use conventional commit messages
2. Keep commits atomic
...
```

Skills are managed through:
- **`common.skills.SkillManager`** -- Python API for listing, reading, saving, and searching skills.
- **Manor `/api/skills` endpoints** -- REST API for the web skill editor.
- **System prompt** -- skill names and descriptions are injected into the prompt so the AI knows what skills are available.

The AI is instructed to read the full skill file when it needs detailed instructions, rather than having all skill content in the prompt.

### Scratchpad (Memory Layer)

The scratchpad at `~/.homestead/scratchpad/` is persistent AI memory. Markdown files here survive across sessions. The system prompt tells the AI about available scratchpad files and encourages their use for persistent context.

---

## Manor API Gateway Architecture

Manor is the web dashboard. It consists of a **Next.js 15 frontend** (TypeScript, React 19, Tailwind CSS 4) and a **FastAPI backend** (Python).

### Backend Structure

```
  manor/api/
    main.py            FastAPI app creation, CORS, router registration
    config.py          Settings singleton (from environment)
    routers/
      sessions.py      Session CRUD (reads Herald's sessions.db)
      logs.py          Log queries (reads watchtower.db)
      skills.py        Skill CRUD (reads/writes ~/.homestead/skills/)
      lore.py          Lore CRUD (reads/writes lore/)
      scratchpad.py    Scratchpad CRUD (reads/writes ~/.homestead/scratchpad/)
      config_routes.py Configuration and agent registry endpoints
      chat.py          WebSocket chat (spawns Claude CLI)
      tasks.py         Task CRUD (reads/writes steward/tasks.db)
      jobs.py          Job CRUD (reads/writes almanac/jobs.db)
```

### Key Design Decision: Self-Contained Routers

Each router file is self-contained. It opens its own SQLite connections, defines its own table schemas (duplicated from the package code), and has no imports from `common`, `herald`, `steward`, or `almanac`. This means:

- Manor can be deployed without any Homestead Python packages installed.
- Adding a new router requires no changes to package code.
- Schema changes must be updated in two places (the package and the router).

The one exception is the `/api/jobs/{job_id}/run` endpoint, which optionally imports `almanac.scheduler` to execute a job action. If the import fails, it falls back to just marking the run.

### WebSocket Chat

The `/ws/chat` endpoint provides real-time chat with Claude. It:

1. Accepts a WebSocket connection.
2. Receives JSON messages with `session_name`, `chat_id`, and `message` fields.
3. Looks up or creates a session in the Herald sessions database.
4. Spawns a Claude CLI subprocess with `--output-format stream-json`.
5. Parses the streaming JSON output and forwards text deltas over the WebSocket.
6. Sends a final `result` message with the complete response and updated session ID.

### CORS

CORS is configured via the `ALLOWED_ORIGINS` environment variable (comma-separated). Defaults to `http://localhost:3000` for local development.

---

## Configuration Cascade

Configuration flows through three layers, from most static to most dynamic:

```
  +------------------+
  | .env files       |  <-- source of truth for secrets and host-specific settings
  +--------+---------+
           |
           v
  +--------+---------+
  | config.py        |  <-- dataclass that loads from os.environ + defaults
  | (per-package)    |      computed properties, type conversion, validation
  +--------+---------+
           |
           v
  +--------+---------+
  | Runtime          |  <-- path resolution, auto-detection, fallbacks
  | (resolved paths, |
  |  lore assembly)  |
  +-----------------+
```

### Layer 1: Environment Variables (.env)

Each service has its own `.env` file (or inherits from the root):

- `/.env` -- shared variables (data dir, API keys)
- `/packages/herald/.env` -- Herald-specific (bot token, allowed users)
- `/manor/api/.env` -- Manor-specific (port, CORS origins)

These are loaded by `python-dotenv` at startup. In Docker, they can be overridden by `docker-compose.yml` `environment` directives.

### Layer 2: Config Dataclasses

Each package has a frozen dataclass that loads from environment with defaults:

**Herald (`herald/config.py`):**
```python
@dataclass(frozen=True)
class Config:
    telegram_bot_token: str          # Required
    allowed_user_ids: list[int]      # Required
    claude_timeout_s: float = 300.0
    streaming_interval_s: float = 1.5
    max_queue_size: int = 5
    session_inactivity_hours: float = 4.0
    max_turns: int = 5
    homestead_data_dir: str = "~/.homestead"
    ...
```

**Manor (`manor/api/config.py`):**
```python
@dataclass(frozen=True)
class Settings:
    homestead_data_dir: str
    herald_data_dir: str
    lore_dir: str
    claude_cli_path: str
    allowed_origins: list[str]
    claude_timeout_s: float = 300.0
    max_turns: int = 10
    port: int = 8700
```

### Layer 3: Runtime Resolution

Some paths are resolved dynamically at load time:

- **`lore_dir`** -- if not set in env, searches for `lore/` relative to the package directory.
- **`herald_data_dir`** -- if not set, tries `packages/herald/data/` then `~/.homestead/herald/`.
- **`system_prompt`** -- assembled at runtime from lore files, skills, and scratchpad (see [Skills and Lore System](#skills-and-lore-system)).

### All Environment Variables

| Variable | Default | Used by |
|---|---|---|
| `HOMESTEAD_DATA_DIR` | `~/.homestead` | All |
| `TELEGRAM_BOT_TOKEN` | (required) | Herald |
| `ALLOWED_USER_IDS` | (required) | Herald |
| `XAI_API_KEY` | (empty) | Herald |
| `ANTHROPIC_API_KEY` | (empty) | Herald |
| `CLAUDE_CLI_PATH` | `claude` | Herald, Manor |
| `CLAUDE_TIMEOUT_S` | `300` | Herald, Manor |
| `MAX_TURNS` | `5` (Herald), `10` (Manor) | Herald, Manor |
| `STREAMING_INTERVAL_S` | `1.5` | Herald |
| `MAX_QUEUE_SIZE` | `5` | Herald |
| `SESSION_INACTIVITY_HOURS` | `4` | Herald |
| `MODEL_ALLOWLIST` | `claude,sonnet,opus,grok` | Herald |
| `SUBAGENT_MODELS` | `grok,sonnet` | Herald |
| `OUTBOX_POLL_INTERVAL_S` | `2.0` | Herald |
| `HERALD_DATA_DIR` | (auto-detected) | Manor |
| `LORE_DIR` | (auto-detected) | Herald, Manor |
| `MANOR_PORT` | `8700` | Manor |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | Manor |

---

## Data Directory Layout

All runtime data lives under `~/.homestead/` (configurable via `HOMESTEAD_DATA_DIR`).

```
~/.homestead/
  watchtower.db                Structured logs (all packages write here)
  outbox.db                    Pending Telegram messages (cross-package)
  steward/
    tasks.db                   Task management database
  almanac/
    jobs.db                    Scheduled job database
  skills/
    git-workflow.md            Example skill file
    code-review.md             Another skill
    ...                        (Markdown files with YAML front-matter)
  scratchpad/
    project-notes.md           Persistent AI memory
    session-context.md         Another note
    ...                        (Markdown files, managed by AI and user)
```

Herald's session database lives separately at `packages/herald/data/sessions.db` (or wherever `HERALD_DATA_DIR` points). This is because sessions are tightly coupled to the Herald bot and not shared infrastructure.

### Docker Volumes

In Docker, the data directory is mapped to a named volume:

```yaml
volumes:
  homestead-data:    # maps to /data/homestead in containers
  herald-data:       # maps to /data/herald (sessions.db)
```

The `lore/` directory is mounted read-only into Herald and read-write into Manor.
