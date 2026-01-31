"""
Hearth Core - Projects System

Multi-day project tracking.
Projects contain multiple tasks and span multiple days.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import json

from .config import Config, get_config
from .tasks import TaskManager

logger = logging.getLogger("hearth.projects")


class Project:
    """A multi-day project."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        status: str = "active",  # active, paused, completed
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        goals: List[str] = None,
        notes: str = ""
    ):
        self.id = id
        self.name = name
        self.description = description
        self.status = status
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
        self.completed_at = completed_at
        self.goals = goals or []
        self.notes = notes

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "goals": self.goals,
            "notes": self.notes
        }

    def to_markdown(self) -> str:
        """Convert project to markdown."""
        md = f"""# Project: {self.name}

**ID:** {self.id}
**Status:** {self.status}
**Created:** {self.created_at}
**Updated:** {self.updated_at}

## Description

{self.description}

## Goals

"""
        for i, goal in enumerate(self.goals, 1):
            md += f"{i}. {goal}\n"

        md += f"""

## Notes

{self.notes}

## Tasks

[Tasks are tracked in the main task system with project='{self.id}']
"""
        return md


class ProjectManager:
    """
    Manages multi-day projects.

    Projects are stored in /home/{entity}/projects/
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.projects_dir = self.config.entity_home / "projects"
        self.active_dir = self.projects_dir / "active"
        self.completed_dir = self.projects_dir / "completed"
        self.paused_dir = self.projects_dir / "paused"

        for dir_path in [self.active_dir, self.completed_dir, self.paused_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def create_project(
        self,
        name: str,
        description: str,
        goals: List[str] = None
    ) -> Project:
        """
        Create a new project.

        Args:
            name: Project name
            description: Project description
            goals: List of goals/objectives

        Returns:
            Created Project object
        """
        # Generate project ID
        project_id = self._generate_id(name)

        project = Project(
            id=project_id,
            name=name,
            description=description,
            goals=goals or []
        )

        # Save to active directory
        self._save_project(project)

        logger.info(f"Created project: {project_id} - {name}")
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID."""
        # Check all directories
        for dir_path in [self.active_dir, self.completed_dir, self.paused_dir]:
            file_path = dir_path / f"{project_id}.json"
            if file_path.exists():
                data = json.loads(file_path.read_text())
                return Project(**data)
        return None

    def list_projects(self, status: str = "active") -> List[Project]:
        """List projects by status."""
        if status == "active":
            dir_path = self.active_dir
        elif status == "completed":
            dir_path = self.completed_dir
        elif status == "paused":
            dir_path = self.paused_dir
        else:
            raise ValueError(f"Invalid status: {status}")

        projects = []
        for file_path in sorted(dir_path.glob("*.json")):
            try:
                data = json.loads(file_path.read_text())
                projects.append(Project(**data))
            except Exception as e:
                logger.warning(f"Failed to load project {file_path.name}: {e}")

        return projects

    def update_project(
        self,
        project_id: str,
        **kwargs
    ) -> bool:
        """Update project fields."""
        project = self.get_project(project_id)
        if not project:
            return False

        # Update fields
        for key, value in kwargs.items():
            if hasattr(project, key):
                setattr(project, key, value)

        project.updated_at = datetime.now().isoformat()

        # Save
        self._save_project(project)
        return True

    def complete_project(self, project_id: str) -> bool:
        """Mark project as completed."""
        project = self.get_project(project_id)
        if not project:
            return False

        project.status = "completed"
        project.completed_at = datetime.now().isoformat()
        project.updated_at = datetime.now().isoformat()

        # Move from active to completed
        old_path = self.active_dir / f"{project_id}.json"
        if old_path.exists():
            old_path.unlink()

        self._save_project(project)
        logger.info(f"Completed project: {project_id}")
        return True

    def pause_project(self, project_id: str) -> bool:
        """Pause a project."""
        project = self.get_project(project_id)
        if not project:
            return False

        project.status = "paused"
        project.updated_at = datetime.now().isoformat()

        # Move from active to paused
        old_path = self.active_dir / f"{project_id}.json"
        if old_path.exists():
            old_path.unlink()

        self._save_project(project)
        logger.info(f"Paused project: {project_id}")
        return True

    def resume_project(self, project_id: str) -> bool:
        """Resume a paused project."""
        project = self.get_project(project_id)
        if not project or project.status != "paused":
            return False

        project.status = "active"
        project.updated_at = datetime.now().isoformat()

        # Move from paused to active
        old_path = self.paused_dir / f"{project_id}.json"
        if old_path.exists():
            old_path.unlink()

        self._save_project(project)
        logger.info(f"Resumed project: {project_id}")
        return True

    def _save_project(self, project: Project):
        """Save project to appropriate directory."""
        if project.status == "active":
            dir_path = self.active_dir
        elif project.status == "completed":
            dir_path = self.completed_dir
        elif project.status == "paused":
            dir_path = self.paused_dir
        else:
            dir_path = self.active_dir

        # Save JSON
        json_path = dir_path / f"{project.id}.json"
        json_path.write_text(json.dumps(project.to_dict(), indent=2))

        # Save markdown
        md_path = dir_path / f"{project.id}.md"
        md_path.write_text(project.to_markdown())

    def _generate_id(self, name: str) -> str:
        """Generate project ID from name."""
        import re
        slug = name.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        slug = slug.strip('-')[:50]  # Max 50 chars

        # Check if exists, add number if needed
        base_slug = slug
        counter = 1
        while self.get_project(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        return slug


# Global instance
_project_manager: Optional[ProjectManager] = None


def get_project_manager(config: Optional[Config] = None) -> ProjectManager:
    """Get or create the global project manager."""
    global _project_manager
    if _project_manager is None:
        _project_manager = ProjectManager(config)
    return _project_manager
