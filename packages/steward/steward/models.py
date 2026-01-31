from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time
import uuid


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"        # waiting on human
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class BlockerType(Enum):
    HUMAN_INPUT = "human_input"       # needs user to provide info
    HUMAN_APPROVAL = "human_approval" # needs user to approve/reject
    HUMAN_ACTION = "human_action"     # needs user to do something external
    DEPENDENCY = "dependency"         # waiting on another task


@dataclass
class Blocker:
    type: BlockerType
    description: str
    created_at: float = field(default_factory=time.time)
    resolved_at: float | None = None
    resolved_by: str | None = None  # "user" or agent name
    resolution: str | None = None   # the actual input/approval


@dataclass
class Task:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    assignee: str = "auto"  # "auto" for AI, "user" for human, or agent name
    blockers: list[Blocker] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)  # task IDs
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    tags: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    source: str = ""  # which module created this task (e.g. "herald", "almanac", "hearth")
