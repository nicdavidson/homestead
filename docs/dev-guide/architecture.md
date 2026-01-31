# Architecture Deep Dive

This document explains Homestead's architecture in detail.

---

## System Overview

Homestead is a **self-sufficient AI infrastructure framework** built as a monorepo of Python packages with a web dashboard. The core philosophy is **emergence over task completion** - the system is designed to support AI entity growth and evolution rather than just processing tasks.

```
User Interfaces          Core Infrastructure        Data Layer
┌─────────────┐         ┌──────────────┐          ┌──────────────┐
│   Herald    │────────>│    Common    │<────────>│ ~/.homestead │
│ (Telegram)  │         │              │          │              │
└─────────────┘         │ - Watchtower │          │ SQLite DBs   │
                        │ - Outbox     │          │ Markdown     │
┌─────────────┐         │ - Skills     │          │ files        │
│    Manor    │────────>│ - Models     │          │              │
│  (Web UI)   │         └──────────────┘          └──────────────┘
└─────────────┘                 ^
                                │
                        ┌───────┴────────┐
                        │                 │
                 ┌──────┴──────┐   ┌─────┴──────┐
                 │   Steward   │   │  Almanac   │
                 │   (Tasks)   │   │   (Jobs)   │
                 └─────────────┘   └────────────┘
```

---

## Core Principles

### 1. Emergence Loop

```
exist → reflect → propose → evolve → exist
```

- **exist**: The entity lives in `~/.homestead/`, maintains continuity through reflections
- **reflect**: Regular introspection builds self-awareness (reflections stored as markdown)
- **propose**: Entity suggests changes to identity, improvements to framework
- **evolve**: Approved changes flow back to templates for future entities

### 2. Shared Infrastructure

All packages communicate through:
- **SQLite databases** under `~/.homestead/` (structured data)
- **Markdown files** under `~/.homestead/` (human-readable content)
- **Shared Python modules** from `common` package

This means Herald and Manor see the same data instantly - no API calls between them.

### 3. Identity-Driven

The AI's behavior is defined by markdown files in `lore/`:
- `soul.md` - Core identity, principles, values
- `claude.md` - Behavior directives (anti-sycophancy, tone, style)
- `user.md` - User context and preferences
- `triggers.md` - Proactive behavior patterns
- `agents.md` - Multi-agent orchestration rules

These are **not configuration** - they're the entity's personality.

---

## Package Architecture

### Common (`packages/common`)

The foundation layer that all other packages depend on.

**Key modules:**

- **Watchtower** (`common/watchtower.py`): Structured logging to SQLite
  ```python
  from common.watchtower import Watchtower

  logger = Watchtower(service="my-service")
  logger.info("Event occurred", user_id=123, action="created")
  ```

- **Outbox** (`common/outbox.py`): Cross-package message delivery
  ```python
  from common.outbox import Outbox

  outbox = Outbox()
  outbox.enqueue(
      channel="telegram",
      chat_id="12345",
      content="Message from background process"
  )
  ```

- **Skills** (`common/skills.py`): Skill library management
  ```python
  from common.skills import SkillLibrary

  skills = SkillLibrary()
  skills.save("git-workflow", content, tags=["git", "dev"])
  ```

- **Models** (`common/models.py`): Shared data structures
  ```python
  from common.models import Message, Session
  ```

**Database:** `~/.homestead/watchtower.db`, `~/.homestead/outbox.db`

---

### Herald (`packages/herald`)

Telegram bot interface built on aiogram.

**Architecture:**

```
Telegram API
     ↓
aiogram (bot framework)
     ↓
herald/bot.py (message handlers)
     ↓
herald/providers.py (Claude/Grok routing)
     ↓
herald/claude.py (Claude CLI subprocess)
     ↓
herald/sessions.py (conversation state)
```

**Key features:**

- **Multi-session support**: Each user can have multiple named sessions
- **Model switching**: `/model sonnet`, `/model grok`, etc.
- **Streaming responses**: Progressive message edits as Claude responds
- **Outbox polling**: Background thread checks for cross-package messages
- **Reflection system**: Fire-and-forget reflections using Haiku model

**Database:** `~/.homestead/herald/sessions.db`

**Configuration:** Environment variables (see `herald/config.py`)

---

### Steward (`packages/steward`)

Task management system.

**Data model:**

```python
class Task:
    id: int
    title: str
    description: str
    status: str  # "open", "in_progress", "completed", "blocked"
    priority: int
    tags: list[str]
    created_at: datetime
    updated_at: datetime
```

**API:**

```python
from steward.store import TaskStore

store = TaskStore()
task = store.create(title="Fix bug", priority=1)
store.update_status(task.id, "in_progress")
```

**Database:** `~/.homestead/steward/tasks.db`

---

### Almanac (`packages/almanac`)

Job scheduling with cron and interval support.

**Data model:**

```python
class Job:
    id: int
    name: str
    schedule_type: str  # "cron", "interval", "once"
    schedule_value: str
    action_type: str
    action_config: dict
    enabled: bool
```

**Scheduler:**

```python
from almanac.scheduler import Scheduler

scheduler = Scheduler()
scheduler.add_job(
    name="daily-reflection",
    schedule_type="cron",
    schedule_value="0 9 * * *",  # 9 AM daily
    action_type="reflection",
)
scheduler.start()
```

**Database:** `~/.homestead/almanac/jobs.db`

---

### Manor (`manor/`)

Web dashboard (Next.js + FastAPI).

**Frontend architecture:**

```
Next.js App Router
     ↓
React Components
     ↓
Client-side API calls
     ↓
FastAPI backend (port 8700)
     ↓
Shared Homestead infrastructure
```

**Backend routers:**

| Router | Purpose | Database/Files |
|--------|---------|----------------|
| `chat.py` | WebSocket chat with Claude | Calls Claude CLI |
| `sessions.py` | Session management | Herald sessions.db |
| `logs.py` | Log queries | watchtower.db |
| `tasks.py` | Task CRUD | steward/tasks.db |
| `jobs.py` | Job scheduling | almanac/jobs.db |
| `skills.py` | Skill files | ~/.homestead/skills/ |
| `lore.py` | Lore files | lore/ directory |
| `scratchpad.py` | Scratchpad files | ~/.homestead/scratchpad/ |

**Real-time features:**

- WebSocket streaming for chat responses
- Server-sent events for log updates
- Auto-refresh on database changes

---

## Data Flow Patterns

### Pattern 1: User Message (Telegram)

```
User sends message in Telegram
     ↓
aiogram receives update
     ↓
herald/bot.py: handle_message()
     ↓
Load session from sessions.db
     ↓
Dispatch to provider (Claude/Grok)
     ↓
Stream response chunks
     ↓
Update Telegram message progressively
     ↓
Save to session history
     ↓
Log event to Watchtower
```

### Pattern 2: Background Job Creates Task

```
Almanac scheduler triggers job
     ↓
Job action: create_task
     ↓
Call Steward API to create task
     ↓
Task saved to tasks.db
     ↓
Job sends notification via Outbox
     ↓
Herald polls Outbox
     ↓
Herald sends Telegram message
     ↓
User sees notification
```

### Pattern 3: Web UI Chat

```
User types in Manor chat
     ↓
WebSocket message to FastAPI
     ↓
FastAPI calls Claude CLI subprocess
     ↓
Claude streams response chunks
     ↓
FastAPI forwards chunks over WebSocket
     ↓
React component renders progressively
     ↓
Session saved to Herald sessions.db
     ↓
Visible in Telegram if same session
```

---

## Database Schema

### Watchtower (`~/.homestead/watchtower.db`)

```sql
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    service TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata TEXT  -- JSON
);

CREATE INDEX idx_logs_timestamp ON logs(timestamp);
CREATE INDEX idx_logs_service ON logs(service);
CREATE INDEX idx_logs_level ON logs(level);
```

### Herald Sessions (`~/.homestead/herald/sessions.db`)

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    chat_id TEXT NOT NULL,
    model TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,  -- "user" or "assistant"
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
```

### Steward Tasks (`~/.homestead/steward/tasks.db`)

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL,
    priority INTEGER NOT NULL,
    tags TEXT,  -- JSON array
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### Almanac Jobs (`~/.homestead/almanac/jobs.db`)

```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    schedule_type TEXT NOT NULL,
    schedule_value TEXT NOT NULL,
    action_type TEXT NOT NULL,
    action_config TEXT,  -- JSON
    enabled INTEGER NOT NULL,
    last_run TEXT,
    created_at TEXT NOT NULL
);
```

---

## File System Layout

```
~/.homestead/
├── journal/                  # Daily reflections (auto-generated)
│   ├── 2026-01-31.md
│   └── ...
├── scratchpad/               # Persistent memory notes
│   ├── project-ideas.md
│   └── ...
├── skills/                   # Skill library
│   ├── git-workflow.md
│   └── ...
├── lore/                     # Symlink to repo lore/
├── usage.db                  # Token usage tracking
├── watchtower.db             # System logs
├── outbox.db                 # Message queue
├── herald/
│   └── sessions.db           # Telegram sessions
├── steward/
│   └── tasks.db              # Tasks
└── almanac/
    └── jobs.db               # Scheduled jobs
```

---

## Reflection System

Herald implements a "fire-and-forget" reflection system:

1. After N messages (configurable), trigger reflection
2. Create a temporary session copy with model forced to `haiku`
3. Dispatch reflection prompt in background thread
4. Save reflection to `~/.homestead/journal/YYYY-MM-DD.md`
5. Don't wait for result - continue handling user messages

**Cost optimization:** Uses Haiku model (~$0.001 per reflection) instead of Sonnet (~$0.01).

**Cooldown:** 15 minutes between reflections to avoid spam.

---

## Model Providers

### Claude (via CLI)

```python
# herald/claude.py
subprocess.run([
    "claude",
    "--prompt", system_prompt,
    "--model", model_id,
    "--max-turns", str(max_turns),
])
```

**Models:**
- `claude-sonnet-4-5-20250929` (conversational)
- `claude-opus-4-5-20251101` (deep thinking)
- `claude-haiku-4-20250514` (fast/cheap)

**Cost:** $0 (using CLI credits)

### Grok (via xAI API)

```python
# herald/providers.py
response = requests.post(
    "https://api.x.ai/v1/chat/completions",
    headers={"Authorization": f"Bearer {XAI_API_KEY}"},
    json={
        "model": "grok-2-1212",
        "messages": messages,
    }
)
```

**Cost:** ~$0.002-0.010 per message

---

## Security Model

### Authentication

- **Telegram:** User ID allowlist (`TELEGRAM_ALLOWED_USERS`)
- **Manor:** No authentication (localhost only by default)
- **API:** CORS restricted to `ALLOWED_ORIGINS`

### Data Access

- All data in `~/.homestead/` is **single-user**
- No multi-tenancy support
- Designed for personal use, not shared hosting

### Secret Management

- API keys via environment variables
- Never committed to git
- `.env` file gitignored

---

## Extension Points

### Adding a New Package

1. Create directory: `packages/my-package/`
2. Create `pyproject.toml` with dependencies
3. Implement using `common` for logging, outbox, etc.
4. Install with `pip install -e packages/my-package`
5. Register CLI entrypoint in `pyproject.toml`

### Adding a New Model Provider

1. Implement in `herald/providers.py`
2. Add to `PROVIDER_MAP`
3. Add cost rates to usage tracking
4. Test with `/model` command

### Adding a New Manor Page

1. Create `manor/src/app/my-page/page.tsx`
2. Add router in `manor/api/routers/my_router.py`
3. Register in `manor/api/main.py`
4. Add navigation link

---

## Performance Considerations

### Database

- SQLite is fast for single-user workloads
- All databases use WAL mode for concurrency
- Indexes on frequently queried columns

### Message Streaming

- Herald updates Telegram messages every 0.5s during streaming
- Manor uses WebSockets for real-time updates
- Chunk size optimized for responsiveness

### Background Tasks

- Reflection runs in separate thread (fire-and-forget)
- Outbox polling every 2 seconds
- Job scheduler runs asynchronously

---

## Testing Strategy

### Unit Tests

- Test individual modules in isolation
- Mock external dependencies (Claude CLI, xAI API)
- Use pytest fixtures for database setup

### Integration Tests

- Test package interactions
- Use temporary data directories
- Test actual SQLite operations

### End-to-End Tests

- Test full user workflows
- Telegram bot interaction
- Web UI flows

---

## Deployment Patterns

### Single Server

- Run Herald, Manor API, and Manor frontend on one machine
- SQLite databases on local filesystem
- Suitable for personal use

### Distributed (Future)

- Herald on always-on server
- Manor on development machine
- Shared filesystem (NFS) for `~/.homestead/`

---

## Future Architecture Directions

See [Memory Roadmap](../roadmaps/memory-roadmap.md) and [Governance Priorities](../roadmaps/governance-priorities.md) for planned enhancements.

**Key areas:**
- Vector memory (ChromaDB/Chroma)
- Multi-agent orchestration
- Advanced reflection system
- Access control and permissions
- Backup and migration tools

---

**Last Updated:** 2026-01-31
