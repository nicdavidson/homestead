# Steward Package Reference

Steward is the task management system for Homestead. It provides structured task tracking with priorities, blockers, dependencies, and assignees.

---

## Installation

```bash
pip install -e packages/steward
```

---

## Quick Start

```python
from steward.store import TaskStore

# Initialize store
store = TaskStore()

# Create a task
task = store.create(
    title="Research async patterns",
    description="Study Python asyncio and document findings",
    priority="high",
    tags=["research", "python"]
)

# Update task status
store.update_status(task.id, "in_progress")

# Add a note
store.add_note(task.id, "Found great documentation on async/await")

# Mark complete
store.update_status(task.id, "completed")
```

---

## Task Model

```python
@dataclass
class Task:
    id: str                      # UUID
    title: str
    description: str
    status: TaskStatus           # pending, in_progress, blocked, completed, cancelled
    priority: TaskPriority       # low, normal, high, urgent
    assignee: str                # "auto", "user", or agent name
    blockers: list[Blocker]      # What's blocking this task
    depends_on: list[str]        # Task IDs this depends on
    created_at: float            # Unix timestamp
    updated_at: float            # Unix timestamp
    completed_at: float | None
    tags: list[str]
    notes: list[Note]            # Timeline of updates
    source: str                  # "user", "agent", "scheduled", etc.
```

### Task Status

```python
class TaskStatus(Enum):
    PENDING = "pending"          # Not started
    IN_PROGRESS = "in_progress"  # Currently being worked on
    BLOCKED = "blocked"          # Waiting on something
    COMPLETED = "completed"      # Done
    CANCELLED = "cancelled"      # Abandoned
```

### Task Priority

```python
class TaskPriority(Enum):
    LOW = "low"          # Nice to have
    NORMAL = "normal"    # Standard priority
    HIGH = "high"        # Important
    URGENT = "urgent"    # Drop everything
```

### Blocker Types

```python
class BlockerType(Enum):
    HUMAN_INPUT = "human_input"        # Needs user to provide info
    HUMAN_APPROVAL = "human_approval"  # Needs user to approve/reject
    HUMAN_ACTION = "human_action"      # Needs user to do something external
    DEPENDENCY = "dependency"          # Waiting on another task
```

---

## TaskStore API

### Create Tasks

```python
task = store.create(
    title="Task title",
    description="Detailed description",
    priority="high",           # low, normal, high, urgent
    assignee="auto",           # auto, user, or agent name
    tags=["research", "api"],
    source="user"              # user, agent, scheduled
)
```

### Query Tasks

```python
# Get by ID
task = store.get(task_id)

# List all tasks
all_tasks = store.list()

# Filter by status
open_tasks = store.list(status="pending")
blocked_tasks = store.list(status="blocked")

# Filter by priority
urgent_tasks = store.list(priority="urgent")

# Filter by assignee
my_tasks = store.list(assignee="user")
auto_tasks = store.list(assignee="auto")

# Filter by tag
research_tasks = store.list(tag="research")

# Combine filters
high_priority_open = store.list(
    status="pending",
    priority="high"
)
```

### Update Tasks

```python
# Update status
store.update_status(task_id, "in_progress")
store.update_status(task_id, "completed")

# Update priority
store.update(task_id, priority="urgent")

# Update assignee
store.update(task_id, assignee="user")

# Update any field
store.update(
    task_id,
    title="New title",
    description="Updated description",
    tags=["new", "tags"]
)
```

### Blockers

```python
# Add a blocker
store.add_blocker(
    task_id,
    blocker_type="human_approval",
    description="Need approval to proceed with API changes"
)

# Resolve a blocker
store.resolve_blocker(
    task_id,
    blocker_index=0,  # First blocker in list
    resolved_by="user",
    resolution="Approved - proceed with changes"
)

# Automatically changes status to BLOCKED when blocker added
# Automatically changes status to PENDING when last blocker resolved
```

### Dependencies

```python
# Task B depends on Task A completing
store.add_dependency(task_b_id, depends_on=task_a_id)

# Get tasks that depend on this one
dependents = store.get_dependents(task_id)

# Check if task is ready (all dependencies complete)
is_ready = store.is_ready(task_id)
```

### Notes

```python
# Add a note (timeline entry)
store.add_note(
    task_id,
    "Started implementation of auth module"
)

# Notes are timestamped automatically
# Useful for tracking progress without changing status
```

### Delete Tasks

```python
# Hard delete
store.delete(task_id)

# Or mark as cancelled
store.update_status(task_id, "cancelled")
```

---

## Database Schema

**Location:** `~/.homestead/steward/tasks.db`

```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    priority TEXT NOT NULL DEFAULT 'normal',
    assignee TEXT DEFAULT 'auto',
    blockers_json TEXT DEFAULT '[]',
    depends_on_json TEXT DEFAULT '[]',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    completed_at REAL,
    tags_json TEXT DEFAULT '[]',
    notes_json TEXT DEFAULT '[]',
    source TEXT DEFAULT ''
);

CREATE INDEX idx_tasks_status ON tasks (status);
CREATE INDEX idx_tasks_priority ON tasks (priority, status);
```

**Note:** Uses WAL mode with 5 second busy timeout for concurrency.

---

## Command Line Interface

Steward provides a CLI for task management:

```bash
# List tasks
steward list
steward list --status pending
steward list --priority high

# Create task
steward create "Task title" --priority high --tags research,python

# View task
steward show <task-id>

# Update task
steward update <task-id> --status in_progress
steward update <task-id> --priority urgent

# Add note
steward note <task-id> "Progress update"

# Delete task
steward delete <task-id>
```

---

## Integration with Other Packages

### Herald (Telegram Bot)

Tasks can be managed via Telegram:

```
/tasks - List all tasks
/task <id> - Show task details
/task new <title> - Create new task
/task done <id> - Mark task complete
```

### Almanac (Job Scheduler)

Tasks can be created by scheduled jobs:

```python
# In Almanac job config
{
    "action_type": "create_task",
    "action_config": {
        "title": "Daily backup",
        "priority": "normal",
        "source": "scheduled"
    }
}
```

### Manor (Web UI)

Tasks are visible and manageable in the Manor dashboard at `/tasks`.

---

## Usage Patterns

### User-Driven Tasks

```python
# User explicitly creates task
task = store.create(
    title="Review pull request",
    assignee="user",
    priority="high",
    source="user"
)
```

### Agent-Driven Tasks

```python
# Agent creates task autonomously
task = store.create(
    title="Research API rate limits",
    assignee="auto",
    priority="normal",
    source="agent"
)
```

### Scheduled Tasks

```python
# Almanac creates recurring task
task = store.create(
    title="Weekly system backup",
    assignee="auto",
    priority="normal",
    source="scheduled"
)
```

### Human-in-the-Loop

```python
# Agent needs approval
task = store.create(
    title="Deploy to production",
    assignee="auto",
    priority="high",
    source="agent"
)

store.add_blocker(
    task.id,
    blocker_type="human_approval",
    description="Need approval to deploy changes"
)

# Later, user approves
store.resolve_blocker(
    task.id,
    blocker_index=0,
    resolved_by="user",
    resolution="Approved"
)
```

---

## Best Practices

### Task Titles

- Keep concise (< 100 chars)
- Use imperative mood ("Research API", not "Researching API")
- Be specific ("Fix login bug in auth.py" not "Fix bug")

### Descriptions

- Provide context and details
- Include acceptance criteria
- Link to relevant resources

### Priorities

- **LOW**: Nice to have, no deadline
- **NORMAL**: Standard work queue
- **HIGH**: Important, do soon
- **URGENT**: Drop everything, do now

### Tags

- Use for categorization ("bug", "feature", "research")
- Use for tech stack ("python", "api", "frontend")
- Use for project ("homestead", "manor", "herald")

### Notes

- Add notes for progress updates
- Document decisions made
- Track time spent (optional)

---

## Error Handling

```python
from steward.store import TaskStore, TaskNotFoundError

store = TaskStore()

try:
    task = store.get("nonexistent-id")
except TaskNotFoundError:
    print("Task not found")
```

---

## Testing

```bash
# Run Steward tests
pytest packages/steward/tests/

# Test specific functionality
pytest packages/steward/tests/test_store.py::test_create_task
```

---

## Development

### Adding New Task Fields

1. Update `Task` dataclass in `models.py`
2. Update database schema in `store.py`
3. Update serialization in `_row_to_task()` and `_task_to_row()`
4. Run migration to add column

### Custom Task Filters

```python
# Add to TaskStore class
def list_overdue(self, days: int = 7) -> list[Task]:
    """Return tasks older than N days."""
    cutoff = time.time() - (days * 86400)
    return [
        t for t in self.list(status="pending")
        if t.created_at < cutoff
    ]
```

---

**Last Updated:** 2026-01-31
