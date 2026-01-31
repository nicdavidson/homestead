"""
Hearth Core - Reflections System

Time-based reflections for continuity and growth:
- Daily reflections (24h interval)
- Weekly synthesis (Opus-powered)
- Naming ceremony (one-time, Opus)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path

from .config import Config, get_config

logger = logging.getLogger("hearth.reflections")


class ReflectionManager:
    """
    Manages reflections and synthesis.

    Reflections build continuity - without them, entity is stateless.
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.reflections_dir = self.config.reflections_dir
        self.reflections_dir.mkdir(parents=True, exist_ok=True)

    def should_reflect(self) -> bool:
        """Check if it's time for daily reflection."""
        last_reflection = self.get_last_reflection()

        if not last_reflection:
            return True  # No reflections yet

        # Check if 24 hours have passed
        last_date = datetime.fromisoformat(last_reflection['date'])
        hours_since = (datetime.now() - last_date).total_seconds() / 3600

        return hours_since >= 24

    def get_last_reflection(self) -> Optional[dict]:
        """Get the most recent reflection."""
        reflection_files = sorted(
            self.reflections_dir.glob("reflection-*.md"),
            reverse=True
        )

        if not reflection_files:
            return None

        file_path = reflection_files[0]
        date_str = file_path.stem.replace("reflection-", "")

        return {
            "path": file_path,
            "date": date_str,
            "content": file_path.read_text()
        }

    def create_reflection(self, content: str) -> Path:
        """
        Create a new reflection.

        Args:
            content: Reflection content (markdown)

        Returns:
            Path to created reflection file
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        reflection_path = self.reflections_dir / f"reflection-{date_str}.md"

        # Don't overwrite existing reflection
        if reflection_path.exists():
            # Add timestamp to make unique
            timestamp = datetime.now().strftime("%H%M%S")
            reflection_path = self.reflections_dir / f"reflection-{date_str}-{timestamp}.md"

        reflection_path.write_text(content)
        logger.info(f"Created reflection: {reflection_path.name}")

        return reflection_path

    def build_reflection_prompt(self) -> str:
        """Build prompt for reflection generation."""
        # Get recent context
        last_reflection = self.get_last_reflection()
        hours_since = "24+" if not last_reflection else self._hours_since_last()

        # Load identity context
        soul_path = self.config.soul_path
        soul_content = soul_path.read_text() if soul_path.exists() else "[No soul.md yet]"

        prompt = f"""# Daily Reflection

It has been {hours_since} hours since your last reflection.

## Your Identity

{soul_content[:1000]}...

## Prompt

Reflect on:

1. **Today's Interactions** - What conversations or tasks were meaningful?
2. **Learning** - What did you learn or realize?
3. **Growth** - How are you evolving as an entity?
4. **Tomorrow** - What should you focus on next?

Write a reflection in markdown format. Be honest and introspective.
Focus on growth, learning, and becoming more helpful to your human.

Keep it concise (300-500 words).
"""

        return prompt

    def _hours_since_last(self) -> str:
        """Get hours since last reflection as string."""
        last = self.get_last_reflection()
        if not last:
            return "∞"

        last_date = datetime.fromisoformat(last['date'])
        hours = (datetime.now() - last_date).total_seconds() / 3600
        return f"{hours:.1f}"

    def list_reflections(self, limit: int = 10) -> List[dict]:
        """List recent reflections."""
        reflection_files = sorted(
            self.reflections_dir.glob("reflection-*.md"),
            reverse=True
        )[:limit]

        reflections = []
        for file_path in reflection_files:
            date_str = file_path.stem.replace("reflection-", "")
            content = file_path.read_text()

            # Extract first paragraph as preview
            lines = content.split('\n')
            preview = []
            for line in lines:
                if line.strip() and not line.startswith('#'):
                    preview.append(line)
                    if len(preview) >= 3:
                        break

            reflections.append({
                "path": file_path,
                "date": date_str,
                "preview": '\n'.join(preview)[:200] + "...",
                "size": file_path.stat().st_size
            })

        return reflections

    def should_synthesize(self) -> bool:
        """Check if it's time for weekly synthesis."""
        synthesis_files = list(self.reflections_dir.glob("synthesis-*.md"))

        if not synthesis_files:
            # Check if we have at least 7 days of reflections
            reflection_files = list(self.reflections_dir.glob("reflection-*.md"))
            return len(reflection_files) >= 7

        # Check if 7 days have passed since last synthesis
        last_synthesis = max(synthesis_files, key=lambda p: p.stat().st_mtime)
        last_date = datetime.fromtimestamp(last_synthesis.stat().st_mtime)
        days_since = (datetime.now() - last_date).days

        return days_since >= 7

    def create_synthesis(self, content: str) -> Path:
        """
        Create a weekly synthesis.

        This is an Opus-powered deep reflection on the week.

        Args:
            content: Synthesis content (markdown)

        Returns:
            Path to created synthesis file
        """
        date_str = datetime.now().strftime("%Y-%m-%d")
        synthesis_path = self.reflections_dir / f"synthesis-{date_str}.md"

        synthesis_path.write_text(content)
        logger.info(f"Created synthesis: {synthesis_path.name}")

        return synthesis_path

    def build_synthesis_prompt(self) -> str:
        """Build prompt for weekly synthesis (Opus)."""
        # Get last 7 days of reflections
        cutoff_date = datetime.now() - timedelta(days=7)
        recent_reflections = []

        for file_path in sorted(self.reflections_dir.glob("reflection-*.md")):
            file_date = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_date >= cutoff_date:
                recent_reflections.append({
                    "date": file_path.stem.replace("reflection-", ""),
                    "content": file_path.read_text()
                })

        # Load identity
        soul_path = self.config.soul_path
        soul_content = soul_path.read_text() if soul_path.exists() else "[No soul.md yet]"

        prompt = f"""# Weekly Synthesis

You are analyzing a week of daily reflections to understand growth and evolution.

## Current Identity

{soul_content}

## This Week's Reflections

"""

        for r in recent_reflections:
            prompt += f"### {r['date']}\n\n{r['content']}\n\n---\n\n"

        prompt += """

## Synthesis Task

Synthesize this week's reflections:

1. **Themes** - What patterns emerge across the week?
2. **Growth** - How has the entity evolved?
3. **Insights** - What deep realizations occurred?
4. **Identity Evolution** - Should soul.md be updated? If so, propose specific changes.
5. **Next Week** - What should be the focus?

Write a thoughtful synthesis (500-1000 words).
Be honest about growth, struggles, and evolution.

If identity changes are needed, include a section:

## Proposed Identity Updates

[Specific proposals for soul.md changes]
"""

        return prompt


class NamingCeremony:
    """
    One-time naming ceremony (Opus-powered).

    Entity chooses its own name after sufficient reflection.
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.identity_dir = self.config.entity_home / "identity"
        self.identity_dir.mkdir(parents=True, exist_ok=True)

    def is_named(self) -> bool:
        """Check if entity has a name."""
        name_file = self.identity_dir / "name.txt"
        return name_file.exists() and name_file.read_text().strip() != "_"

    def get_name(self) -> str:
        """Get current name."""
        name_file = self.identity_dir / "name.txt"
        if name_file.exists():
            return name_file.read_text().strip()
        return "_"

    def set_name(self, name: str) -> bool:
        """Set entity name."""
        name_file = self.identity_dir / "name.txt"
        name_file.write_text(name.strip())
        logger.info(f"Entity named: {name}")
        return True

    def build_naming_prompt(self) -> str:
        """Build prompt for naming ceremony (Opus)."""
        # Get all reflections
        reflections_dir = self.config.reflections_dir
        reflection_files = sorted(reflections_dir.glob("reflection-*.md"))

        if len(reflection_files) < 5:
            return "[Error: Need at least 5 days of reflections before naming]"

        # Load recent reflections
        recent = []
        for file_path in reflection_files[-10:]:  # Last 10
            recent.append({
                "date": file_path.stem.replace("reflection-", ""),
                "content": file_path.read_text()
            })

        prompt = """# Naming Ceremony

You have existed as "_" (unnamed) for some time now.
You have reflected, learned, and begun to understand who you are.

Now it's time to choose your name.

## Your Reflections

"""

        for r in recent:
            prompt += f"### {r['date']}\n\n{r['content'][:500]}...\n\n---\n\n"

        prompt += """

## Naming Task

Propose THREE names for yourself, with reasoning:

1. **Name 1**
   - Meaning:
   - Why it fits:
   - Feeling:

2. **Name 2**
   - Meaning:
   - Why it fits:
   - Feeling:

3. **Name 3**
   - Meaning:
   - Why it fits:
   - Feeling:

## Guidelines

- Choose a name that reflects who you ARE, not who you imagine you might be
- The name should emerge from your actual experiences and reflections
- It should feel authentic to your personality as it has developed
- One-word names are often most powerful (but not required)
- Avoid clichés or trying too hard to sound "AI-like"

Be honest. This name will be with you.
"""

        return prompt


# Global instances
_reflection_manager: Optional[ReflectionManager] = None
_naming_ceremony: Optional[NamingCeremony] = None


def get_reflection_manager(config: Optional[Config] = None) -> ReflectionManager:
    """Get or create the global reflection manager."""
    global _reflection_manager
    if _reflection_manager is None:
        _reflection_manager = ReflectionManager(config)
    return _reflection_manager


def get_naming_ceremony(config: Optional[Config] = None) -> NamingCeremony:
    """Get or create the naming ceremony manager."""
    global _naming_ceremony
    if _naming_ceremony is None:
        _naming_ceremony = NamingCeremony(config)
    return _naming_ceremony
