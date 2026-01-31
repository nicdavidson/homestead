# Common Package Reference

The `homestead-common` package provides shared infrastructure used by all Homestead packages.

---

## Installation

```bash
pip install -e packages/common
```

---

## Modules

### Watchtower (Logging)

Structured logging to SQLite with queryable metadata.

**Import:**
```python
from common.watchtower import Watchtower
```

**Basic usage:**
```python
logger = Watchtower(service="my-service")

# Simple log
logger.info("User logged in")

# With metadata
logger.info("Task created", task_id=123, priority="high")

# Different levels
logger.debug("Debug info", details={"foo": "bar"})
logger.warning("Potential issue", code=42)
logger.error("Error occurred", error=str(exception))
```

**Query logs:**
```python
from common.watchtower import Watchtower

wt = Watchtower("query")
logs = wt.query(
    service="herald",
    level="ERROR",
    since="2026-01-30",
    limit=50
)

for log in logs:
    print(f"{log.timestamp} [{log.level}] {log.message}")
    print(f"  Metadata: {log.metadata}")
```

**Database:** `~/.homestead/watchtower.db`

**Schema:**
```sql
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    service TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata TEXT  -- JSON
);
```

---

### Outbox (Message Queue)

Cross-package message delivery system. Allows background processes to send messages to users via Herald.

**Import:**
```python
from common.outbox import post_message, get_pending, mark_sent, mark_failed
```

**Send a message:**
```python
post_message(
    channel="telegram",
    chat_id="12345",
    content="Task completed successfully!",
    metadata={"task_id": 123}
)
```

**Poll for messages (Herald does this):**
```python
messages = get_pending()
for msg in messages:
    try:
        # Send via Telegram/Discord/etc
        await bot.send_message(msg.chat_id, msg.content)
        mark_sent(msg.id)
    except Exception as e:
        mark_failed(msg.id, str(e))
```

**Database:** `~/.homestead/outbox.db`

**Schema:**
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT NOT NULL,
    chat_id TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata TEXT,
    status TEXT NOT NULL,  -- 'pending', 'sent', 'failed'
    created_at TEXT NOT NULL,
    sent_at TEXT,
    error TEXT
);
```

---

### Skills (Skill Library)

Manage markdown skill files that can be injected into AI context.

**Import:**
```python
from common.skills import SkillLibrary
```

**Save a skill:**
```python
skills = SkillLibrary()

content = """
# Git Workflow

Common git commands:
```bash
git status
git add .
git commit -m "message"
git push
```
"""

skills.save("git-workflow", content, tags=["git", "dev"])
```

**Load a skill:**
```python
skill = skills.load("git-workflow")
print(skill.content)
```

**List skills:**
```python
all_skills = skills.list()
for skill in all_skills:
    print(f"{skill.name} - tags: {skill.tags}")
```

**Search by tag:**
```python
dev_skills = skills.search(tag="dev")
```

**File location:** `~/.homestead/skills/<skill-name>.md`

---

### Models (Shared Data Structures)

Common data models used across packages.

**Import:**
```python
from common.models import AgentIdentity, LogEntry, AGENTS, format_agent_message
```

**AgentIdentity:**
```python
class AgentIdentity:
    name: str
    emoji: str
    color: str
    personality: str
```

**Available agents:**
```python
from common.models import AGENTS

AGENTS = {
    "herald": AgentIdentity(
        name="Herald",
        emoji="📯",
        color="blue",
        personality="Conversational assistant"
    ),
    "steward": AgentIdentity(
        name="Steward",
        emoji="📋",
        color="green",
        personality="Task manager"
    ),
    # ... more agents
}
```

**Format messages:**
```python
from common.models import format_agent_message

msg = format_agent_message(
    agent="herald",
    content="Task completed!",
    include_emoji=True
)
# Returns: "📯 **Herald:** Task completed!"
```

---

### Events (Event Bus)

Pub/sub event system for cross-package communication.

**Import:**
```python
from common.events import EventBus
```

**Subscribe to events:**
```python
bus = EventBus()

def on_task_created(event):
    print(f"Task {event.task_id} created!")

bus.subscribe("task.created", on_task_created)
```

**Publish events:**
```python
bus.publish("task.created", task_id=123, title="New task")
```

**Unsubscribe:**
```python
bus.unsubscribe("task.created", on_task_created)
```

---

### Database (Connection Management)

Unified SQLite connection handling.

**Import:**
```python
from common.db import get_connection
```

**Get a database connection:**
```python
conn = get_connection("tasks")  # Opens ~/.homestead/tasks.db
cursor = conn.cursor()
cursor.execute("SELECT * FROM tasks")
results = cursor.fetchall()
conn.close()
```

**Context manager:**
```python
from common.db import get_connection

with get_connection("watchtower") as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM logs")
    count = cursor.fetchone()[0]
```

---

### Alerts (Alert System)

System for tracking and managing alerts.

**Import:**
```python
from common.alerts import AlertManager
```

**Create an alert:**
```python
alerts = AlertManager()

alerts.create(
    level="warning",
    title="High memory usage",
    message="System memory usage above 80%",
    source="system-monitor"
)
```

**Get active alerts:**
```python
active = alerts.get_active()
for alert in active:
    print(f"[{alert.level}] {alert.title}")
```

**Acknowledge/dismiss:**
```python
alerts.acknowledge(alert_id=1)
alerts.dismiss(alert_id=1)
```

---

## Environment Variables

The common package respects these environment variables:

```bash
# Data directory (required)
HOMESTEAD_DATA_DIR=~/.homestead

# Optional overrides
WATCHTOWER_DB=~/.homestead/watchtower.db
OUTBOX_DB=~/.homestead/outbox.db
SKILLS_DIR=~/.homestead/skills
```

---

## File Structure

After initialization, the common package creates:

```
~/.homestead/
├── watchtower.db      # Logs
├── outbox.db          # Message queue
└── skills/            # Skill library
    ├── skill-1.md
    └── skill-2.md
```

---

## Testing

```bash
# Run common package tests
pytest packages/common/tests/

# Test specific module
pytest packages/common/tests/test_watchtower.py
```

---

## Best Practices

### Logging

- Use structured metadata instead of string interpolation
- Choose appropriate log levels (debug/info/warning/error)
- Include context (user_id, task_id, etc.) in metadata

**Good:**
```python
logger.info("Task completed", task_id=123, duration_ms=4500)
```

**Bad:**
```python
logger.info(f"Task {task_id} completed in {duration}ms")
```

### Outbox

- Keep messages concise
- Include metadata for context
- Handle failures gracefully
- Don't spam - batch notifications when possible

### Skills

- Write self-contained, reusable content
- Use markdown formatting
- Tag appropriately for discoverability
- Keep skills focused (one topic per skill)

---

**Last Updated:** 2026-01-31
