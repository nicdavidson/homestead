"""
Hearth Core - Skills System

Dynamic capability learning. Entity can:
- Learn new skills from experience
- Store skills as markdown files
- Load skills dynamically as tools
- Build skill library over time
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import json

from .config import Config, get_config

logger = logging.getLogger("hearth.skills")


class Skill:
    """A learned skill."""

    def __init__(
        self,
        name: str,
        description: str,
        content: str,
        examples: List[str] = None,
        tags: List[str] = None,
        created_at: Optional[str] = None
    ):
        self.name = name
        self.description = description
        self.content = content
        self.examples = examples or []
        self.tags = tags or []
        self.created_at = created_at or datetime.now().isoformat()

    def to_markdown(self) -> str:
        """Convert skill to markdown format."""
        md = f"""# Skill: {self.name}

**Description:** {self.description}

**Created:** {self.created_at}

**Tags:** {', '.join(self.tags) if self.tags else 'none'}

## Content

{self.content}

"""

        if self.examples:
            md += "\n## Examples\n\n"
            for i, example in enumerate(self.examples, 1):
                md += f"### Example {i}\n\n{example}\n\n"

        return md

    @classmethod
    def from_markdown(cls, content: str) -> 'Skill':
        """Parse skill from markdown."""
        lines = content.split('\n')

        # Extract metadata
        name = ""
        description = ""
        tags = []
        created_at = None
        skill_content = []
        examples = []

        in_content = False
        in_examples = False
        current_example = []

        for line in lines:
            if line.startswith('# Skill:'):
                name = line.replace('# Skill:', '').strip()
            elif line.startswith('**Description:**'):
                description = line.replace('**Description:**', '').strip()
            elif line.startswith('**Tags:**'):
                tags_str = line.replace('**Tags:**', '').strip()
                if tags_str != 'none':
                    tags = [t.strip() for t in tags_str.split(',')]
            elif line.startswith('**Created:**'):
                created_at = line.replace('**Created:**', '').strip()
            elif line.startswith('## Content'):
                in_content = True
                in_examples = False
            elif line.startswith('## Examples'):
                in_content = False
                in_examples = True
            elif line.startswith('### Example'):
                if current_example:
                    examples.append('\n'.join(current_example))
                current_example = []
            elif in_content:
                skill_content.append(line)
            elif in_examples and line.strip():
                current_example.append(line)

        # Add last example
        if current_example:
            examples.append('\n'.join(current_example))

        return cls(
            name=name,
            description=description,
            content='\n'.join(skill_content).strip(),
            examples=examples,
            tags=tags,
            created_at=created_at
        )


class SkillManager:
    """
    Manages entity skills.

    Skills are stored as markdown files in /home/{entity}/skills/learned/
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.skills_dir = self.config.entity_home / "skills" / "learned"
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def create_skill(
        self,
        name: str,
        description: str,
        content: str,
        examples: List[str] = None,
        tags: List[str] = None
    ) -> Skill:
        """
        Create a new skill.

        Args:
            name: Skill name (will be slugified for filename)
            description: Short description
            content: Skill content (how to use it)
            examples: List of usage examples
            tags: List of tags for categorization

        Returns:
            Created Skill object
        """
        skill = Skill(
            name=name,
            description=description,
            content=content,
            examples=examples,
            tags=tags
        )

        # Save to file
        filename = self._slugify(name) + ".md"
        file_path = self.skills_dir / filename

        file_path.write_text(skill.to_markdown())
        logger.info(f"Created skill: {name} ({filename})")

        return skill

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        filename = self._slugify(name) + ".md"
        file_path = self.skills_dir / filename

        if not file_path.exists():
            return None

        content = file_path.read_text()
        return Skill.from_markdown(content)

    def list_skills(self, tag: Optional[str] = None) -> List[Skill]:
        """List all skills, optionally filtered by tag."""
        skills = []

        for file_path in sorted(self.skills_dir.glob("*.md")):
            try:
                content = file_path.read_text()
                skill = Skill.from_markdown(content)

                # Filter by tag if specified
                if tag and tag not in skill.tags:
                    continue

                skills.append(skill)
            except Exception as e:
                logger.warning(f"Failed to load skill {file_path.name}: {e}")

        return skills

    def delete_skill(self, name: str) -> bool:
        """Delete a skill."""
        filename = self._slugify(name) + ".md"
        file_path = self.skills_dir / filename

        if not file_path.exists():
            return False

        file_path.unlink()
        logger.info(f"Deleted skill: {name}")
        return True

    def search_skills(self, query: str) -> List[Skill]:
        """Search skills by name, description, or content."""
        query_lower = query.lower()
        results = []

        for skill in self.list_skills():
            if (query_lower in skill.name.lower() or
                query_lower in skill.description.lower() or
                query_lower in skill.content.lower()):
                results.append(skill)

        return results

    def get_skill_tags(self) -> List[str]:
        """Get all unique tags across skills."""
        tags = set()
        for skill in self.list_skills():
            tags.update(skill.tags)
        return sorted(tags)

    def build_skill_prompt(self, skill_name: str) -> str:
        """Build a prompt to learn a new skill."""
        return f"""# Learning New Skill: {skill_name}

You are learning a new skill based on recent experience.

## Task

Create a skill that captures:

1. **What** the skill does
2. **When** to use it
3. **How** to use it (step by step)
4. **Examples** of usage

## Format

Provide:

- **Name:** {skill_name}
- **Description:** (one sentence)
- **Content:** (detailed explanation)
- **Examples:** (2-3 practical examples)
- **Tags:** (2-3 relevant tags)

## Guidelines

- Be specific and practical
- Include actual code/commands if relevant
- Make it reusable for future situations
- Focus on what worked

Write the skill in a way that your future self can use it effectively.
"""

    def _slugify(self, name: str) -> str:
        """Convert skill name to filename-safe slug."""
        import re
        slug = name.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')


# Global instance
_skill_manager: Optional[SkillManager] = None


def get_skill_manager(config: Optional[Config] = None) -> SkillManager:
    """Get or create the global skill manager."""
    global _skill_manager
    if _skill_manager is None:
        _skill_manager = SkillManager(config)
    return _skill_manager
