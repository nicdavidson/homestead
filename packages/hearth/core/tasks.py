"""
Hearth Core - Task Management

Wraps StateDB task methods with convenience functions.
StateDB already has a task system - we just add a cleaner interface.
"""

from typing import List, Optional, Dict
import logging

from .config import Config, get_config
from .state import StateDB, get_state

logger = logging.getLogger("hearth.tasks")


class TaskManager:
    """
    Manages tasks (TODOs).

    Wraps StateDB's existing task system with a cleaner interface.
    """

    def __init__(self, config: Optional[Config] = None, state: Optional[StateDB] = None):
        self.config = config or get_config()
        self.state = state or get_state(str(self.config.data_dir / "hearth.db"))

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: int = 3,
        source: str = "manual",
        project: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Create a new task.

        Args:
            title: Short task title
            description: Detailed description
            priority: 1-5 (1=highest, 5=lowest)
            source: Task source (manual, entity, nightshift, etc.)
            project: Optional project name
            metadata: Optional metadata dict

        Returns:
            Task ID
        """
        task_id = self.state.add_task(
            title=title,
            description=description,
            priority=priority,
            source=source,
            project=project,
            metadata=metadata or {}
        )

        logger.info(f"Created task: {task_id} - {title}")
        return task_id

    def list_tasks(
        self,
        status: Optional[str] = None,
        project: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        List tasks with optional filters.

        Args:
            status: Filter by status (pending, in_progress, completed, failed)
            project: Filter by project name
            limit: Limit number of results

        Returns:
            List of task dicts
        """
        if status:
            tasks = self.state.get_tasks_by_status(status)
        else:
            # Get all non-completed tasks
            tasks = (
                self.state.get_tasks_by_status("pending") +
                self.state.get_tasks_by_status("in_progress")
            )

        # Filter by project if specified
        if project:
            tasks = [t for t in tasks if t.get('project') == project]

        # Apply limit if specified
        if limit:
            tasks = tasks[:limit]

        return tasks

    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get a task by ID."""
        return self.state.get_task(task_id)

    def start_task(self, task_id: str) -> bool:
        """Mark task as in_progress."""
        success = self.state.update_task(task_id, status="in_progress")
        if success:
            logger.info(f"Started task: {task_id}")
        return success

    def complete_task(self, task_id: str, result: str = "") -> bool:
        """Mark task as completed."""
        success = self.state.complete_task(task_id, result=result)
        if success:
            logger.info(f"Completed task: {task_id}")
        return success

    def fail_task(self, task_id: str, error: str) -> bool:
        """Mark task as failed."""
        success = self.state.fail_task(task_id, error=error)
        if success:
            logger.error(f"Failed task: {task_id} - {error}")
        return success

    def update_task(self, task_id: str, **kwargs) -> bool:
        """Update task fields."""
        return self.state.update_task(task_id, **kwargs)

    def get_stats(self) -> Dict:
        """Get task statistics."""
        return self.state.get_task_stats()

    def get_pending(self, limit: int = 10) -> List[Dict]:
        """Get pending tasks ordered by priority."""
        return self.state.get_pending_tasks(limit=limit)

    def get_next(self) -> Optional[Dict]:
        """Get the next task to process."""
        return self.state.get_next_task()


# Global instance
_task_manager: Optional[TaskManager] = None


def get_task_manager(config: Optional[Config] = None) -> TaskManager:
    """Get or create the global task manager."""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager(config)
    return _task_manager
