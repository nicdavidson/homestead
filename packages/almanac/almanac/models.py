from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import time
import uuid


class ScheduleType(Enum):
    CRON = "cron"          # cron expression
    INTERVAL = "interval"  # every N seconds/minutes/hours
    ONCE = "once"          # one-shot at specific time


class JobStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"  # for one-shot jobs that have fired
    DISABLED = "disabled"


@dataclass
class Schedule:
    type: ScheduleType
    expression: str  # cron: "0 9 * * *", interval: "30m", once: ISO timestamp
    timezone: str = "UTC"


@dataclass
class JobAction:
    """What to do when the job fires."""
    type: str  # "notify", "create_task", "run_command", "webhook"
    config: dict[str, Any] = field(default_factory=dict)
    # notify: {"channel": "telegram", "message": "..."}
    # create_task: {"title": "...", "assignee": "auto", "tags": [...]}
    # run_command: {"command": "...", "cwd": "..."}


@dataclass
class Job:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    schedule: Schedule | None = None
    action: JobAction | None = None
    status: JobStatus = JobStatus.ACTIVE
    last_run_at: float | None = None
    next_run_at: float | None = None
    run_count: int = 0
    created_at: float = field(default_factory=time.time)
    tags: list[str] = field(default_factory=list)
    source: str = ""  # which module created this
