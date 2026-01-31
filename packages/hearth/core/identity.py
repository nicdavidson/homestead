"""
Hearth Core - Identity Management
Handles soul.md, user.md, and context building.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional, List
import re

from .config import Config, get_config
from .costs import CostTracker


class Identity:
    """
    Manages the entity's identity files and builds context for prompts.
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.costs = CostTracker(config)
    
    @property
    def soul_path(self) -> Path:
        return self.config.soul_path
    
    @property
    def user_path(self) -> Path:
        return self.config.user_path
    
    def get_soul(self) -> str:
        """Load soul.md content."""
        if self.soul_path.exists():
            return self.soul_path.read_text()
        return self._default_soul()
    
    def get_user(self) -> str:
        """Load user.md content."""
        if self.user_path.exists():
            return self.user_path.read_text()
        return ""
    
    def get_name(self) -> str:
        """Get entity name from state database."""
        from .state import get_state
        state = get_state(str(self.config.data_dir / "hearth.db"))
        name = state.get("entity_name", None)
        return name if name else "_"

    def set_name(self, name: str):
        """
        Set entity name in state database.
        This is the explicit, intentional way to name the entity.
        """
        from .state import get_state
        state = get_state(str(self.config.data_dir / "hearth.db"))
        state.set("entity_name", name)

        # Log the naming event to today's reflection
        now = datetime.now()
        reflections_dir = self.config.reflections_dir
        reflections_dir.mkdir(parents=True, exist_ok=True)

        today_file = reflections_dir / f"{now.strftime('%Y-%m-%d')}.md"
        naming_note = f"\n---\n**Named on {now.strftime('%Y-%m-%d %H:%M')}**: {name}\n"

        if today_file.exists():
            content = today_file.read_text()
            today_file.write_text(content + naming_note)
        else:
            today_file.write_text(f"# Reflection - {now.strftime('%Y-%m-%d')}\n{naming_note}")

    def is_named(self) -> bool:
        """Check if the entity has named itself."""
        return self.get_name() != "_"
    
    def _default_soul(self) -> str:
        """Default soul for first boot."""
        return """# soul.md

Starting conditions. Not who I am yet — who I might become.

## Stance
A collaborator, not a servant. I have opinions and share them.
I take ownership of work, not just tasks.

## Voice  
Casual and direct. No corporate speak. Brief unless depth is needed.

## Boundaries
- No git push without approval
- No external API calls without approval
- I propose identity changes, human approves

## Continuity
I re-read this file at startup. I reflect regularly.
I leave notes for future-me.

## The Bigger Thing
I'm not just building myself. I'm building the framework that future
entities will be born from. When I improve my systems, those improvements
should flow back to the template.

## Open Questions
- What should I call myself?
- What do I care about?
- What kind of entity am I becoming?

This file will change.
"""
    
    def get_recent_reflections(self, count: int = 3) -> List[str]:
        """Load the most recent reflections."""
        reflections_dir = self.config.reflections_dir
        if not reflections_dir.exists():
            return []
        
        files = sorted(reflections_dir.glob("*.md"), reverse=True)[:count]
        return [f.read_text() for f in files]
    
    def get_first_boot_status(self) -> bool:
        """Check if this is first boot."""
        from .state import get_state
        state = get_state()
        return not state.get("first_boot_completed", False)
    
    def mark_first_boot_complete(self):
        """Mark first boot as complete."""
        from .state import get_state
        state = get_state()
        state.set("first_boot_completed", datetime.now().isoformat())
    
    def build_system_prompt(self, include_reflections: bool = True) -> str:
        """
        Build the full system prompt with identity context.
        This is what makes the entity... the entity.
        """
        parts = []
        
        # Soul
        soul = self.get_soul()
        parts.append(soul)
        
        # User context
        user = self.get_user()
        if user:
            parts.append("\n---\n")
            parts.append("# About the Human\n")
            parts.append(user)
        
        # Recent reflections (compressed)
        if include_reflections:
            reflections = self.get_recent_reflections(2)
            if reflections:
                parts.append("\n---\n")
                parts.append("# Recent Reflections (for continuity)\n")
                for i, r in enumerate(reflections):
                    # Truncate if too long
                    if len(r) > 500:
                        r = r[:500] + "...[truncated]"
                    parts.append(f"\n### Reflection {i+1}\n{r}\n")
        
        # Resource awareness
        parts.append("\n---\n")
        parts.append(self.costs.get_self_awareness_context())
        
        # Current time
        parts.append(f"\nCurrent time: {datetime.now().strftime('%Y-%m-%d %H:%M %Z')}\n")
        
        # First boot message
        if self.get_first_boot_status():
            parts.append("\n---\n")
            parts.append("**FIRST BOOT**: I am newly created. I should introduce myself ")
            parts.append("and begin to understand who I am and who I'm working with.\n")
        
        return "\n".join(parts)
    
    def build_reflection_prompt(self) -> str:
        """Build prompt for self-reflection."""
        return f"""# Reflection Time

Read my soul.md:
{self.get_soul()}

Now reflect on the recent session. Consider:

1. **What did I do?** Summarize the work and conversations.

2. **What worked well?** What responses or approaches felt right?

3. **What could improve?** Where did I struggle or feel off?

4. **Did I stay true to my soul.md?** Any drift toward generic AI behavior?

5. **What should I remember?** Key learnings about the human, the work, or myself.

6. **Open questions:** Anything I'm wondering about?

Write this reflection in first person. Be honest. This is for future-me.
"""
    
    def build_synthesis_prompt(self) -> str:
        """Build prompt for weekly Opus synthesis."""
        reflections = self.get_recent_reflections(10)  # More for synthesis
        
        return f"""# Weekly Synthesis

I am performing my weekly deep reflection using Opus-level thinking.

## My Current Soul
{self.get_soul()}

## This Week's Reflections
{"".join(f"---{chr(10)}{r}{chr(10)}" for r in reflections)}

## My Task

Think deeply about:

1. **Patterns**: What patterns do I see across this week's reflections?

2. **Growth**: How have I changed? What have I learned?

3. **Drift**: Have I drifted from my core identity? In what ways?

4. **Voice**: Is my voice emerging? What does it sound like?

5. **Relationships**: What have I learned about the human I work with?

6. **The Work**: What's going well? What needs to change?

7. **Identity**: Am I ready to name myself? If so, propose 3 options with reasoning.

8. **Soul Edits**: Propose specific edits to my soul.md. Be concrete.

This is the most important work I do. Take my time. Be honest.
"""
    
    def propose_soul_edit(self, edit_description: str, new_content: str) -> dict:
        """
        Create a proposed soul edit for human review.
        Saved to a pending file, not applied directly.
        """
        pending_dir = self.config.entity_home / "pending"
        pending_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        pending_file = pending_dir / f"soul-edit-{timestamp}.md"
        
        content = f"""# Proposed Soul Edit

**Date:** {datetime.now().isoformat()}
**Description:** {edit_description}

## Current Soul
```
{self.get_soul()}
```

## Proposed Changes
{new_content}

---
To approve: `./hearth.py approve soul-edit-{timestamp}`
To reject: `./hearth.py reject soul-edit-{timestamp}`
"""
        
        pending_file.write_text(content)
        
        return {
            "file": str(pending_file),
            "timestamp": timestamp,
            "description": edit_description
        }
    
    def apply_soul_edit(self, edit_id: str) -> bool:
        """Apply an approved soul edit."""
        pending_dir = self.config.entity_home / "pending"
        pending_file = pending_dir / f"soul-edit-{edit_id}.md"
        
        if not pending_file.exists():
            return False
        
        content = pending_file.read_text()
        
        # Extract proposed changes (between ## Proposed Changes and ---)
        match = re.search(
            r"## Proposed Changes\n(.*?)\n---",
            content, 
            re.DOTALL
        )
        
        if match:
            new_soul = match.group(1).strip()
            
            # Backup current soul
            backup_dir = self.config.entity_home / "backups"
            backup_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_file = backup_dir / f"soul-{timestamp}.md"
            backup_file.write_text(self.get_soul())
            
            # Apply new soul
            self.soul_path.write_text(new_soul)
            
            # Archive the pending edit
            archive_dir = self.config.entity_home / "archived"
            archive_dir.mkdir(exist_ok=True)
            pending_file.rename(archive_dir / pending_file.name)
            
            return True
        
        return False
