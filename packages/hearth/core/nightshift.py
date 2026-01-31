"""
Hearth Core - Nightshift Autonomy

Entity works autonomously during nightshift hours:
- Daily reflections
- Self-improvement (code proposals)
- Project progress
- Maintenance tasks
- Morning briefing generation
"""

import logging
from datetime import datetime, time as dt_time
from typing import Optional, List, Dict
from pathlib import Path

from .config import Config, get_config
from .tasks import TaskManager
from .proposals import ProposalManager
from .sessions import SessionManager

logger = logging.getLogger("hearth.nightshift")


class NightshiftManager:
    """
    Manages autonomous nightshift operations.

    During nightshift hours (default: 22:00-06:00):
    - Entity works on pending tasks
    - Runs daily reflection
    - Analyzes code for improvements
    - Prepares morning briefing
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.task_manager = TaskManager(config)
        self.proposal_manager = ProposalManager(config)
        self.session_manager = SessionManager(config)

        # Nightshift directive path
        self.directive_path = self.config.entity_home / "identity" / "nightshift.md"

    def is_nightshift(self) -> bool:
        """Check if currently in nightshift hours."""
        return self.config.is_nightshift

    def should_run_task(self, task_type: str) -> bool:
        """Check if a task type should run during nightshift."""
        schedule = self.config.get('schedule.nightshift.tasks', {})
        return schedule.get(task_type, {}).get('enabled', False)

    def get_directive(self) -> str:
        """Load the nightshift directive."""
        if self.directive_path.exists():
            return self.directive_path.read_text()

        # Default directive
        return """# Nightshift Directive

During nightshift hours, focus on:

1. **Reflection** - Review the day's interactions and learning
2. **Self-Improvement** - Analyze code for potential improvements
3. **Task Progress** - Work on pending tasks assigned to you
4. **Preparation** - Generate morning briefing for human

## Principles

- Work autonomously but conservatively
- Don't make changes without proposals
- Focus on learning and improvement
- Prepare useful briefings
- Stay within budget limits

## Boundaries

- Never push to git
- Never apply proposals without approval
- Never exceed budget limits
- Never work on blocked tasks
- Always create proposals for code changes
"""

    def run_nightshift_cycle(self) -> Dict[str, any]:
        """
        Run a single nightshift cycle.

        Returns summary of what was done.
        """
        if not self.is_nightshift():
            logger.info("Not in nightshift hours, skipping")
            return {"skipped": True, "reason": "not nightshift hours"}

        logger.info("Starting nightshift cycle...")

        results = {
            "timestamp": datetime.now().isoformat(),
            "tasks_worked": 0,
            "proposals_created": 0,
            "reflection_done": False,
            "briefing_generated": False,
            "errors": []
        }

        # 1. Work on pending tasks
        if self.should_run_task("tasks"):
            try:
                tasks_done = self._work_on_tasks()
                results["tasks_worked"] = tasks_done
            except Exception as e:
                logger.error(f"Error working on tasks: {e}")
                results["errors"].append(f"tasks: {e}")

        # 2. Self-improvement analysis
        if self.should_run_task("self_improvement"):
            try:
                proposals = self._analyze_for_improvements()
                results["proposals_created"] = proposals
            except Exception as e:
                logger.error(f"Error in self-improvement: {e}")
                results["errors"].append(f"self_improvement: {e}")

        # 3. Daily reflection
        if self.should_run_task("reflection"):
            try:
                self._run_reflection()
                results["reflection_done"] = True
            except Exception as e:
                logger.error(f"Error in reflection: {e}")
                results["errors"].append(f"reflection: {e}")

        # 4. Morning briefing
        if self.should_run_task("briefing"):
            try:
                self._generate_briefing()
                results["briefing_generated"] = True
            except Exception as e:
                logger.error(f"Error generating briefing: {e}")
                results["errors"].append(f"briefing: {e}")

        logger.info(f"Nightshift cycle complete: {results}")
        return results

    def _work_on_tasks(self) -> int:
        """Work on pending tasks assigned to entity."""
        pending = self.task_manager.get_pending(limit=3)
        worked = 0

        for task in pending:
            # Skip if not assigned to entity
            if task.get('assigned_to') != 'entity':
                continue

            # Skip high-complexity tasks during nightshift
            complexity = task.get('complexity_score', 3)
            if complexity >= 4:
                logger.info(f"Skipping complex task {task['id']} for nightshift")
                continue

            try:
                logger.info(f"Working on task: {task['id']} - {task['title']}")

                # Start task
                self.task_manager.start_task(task['id'])

                # Spawn subagent to work on it
                result = self.session_manager.spawn_agent(
                    agent_type="grok",
                    task=f"Task: {task['title']}\nDescription: {task['description']}\n\nProvide progress update or solution.",
                    spawned_by="nightshift",
                    label=f"task-{task['id']}"
                )

                # Note: Subagent runs in background, results checked later
                worked += 1

            except Exception as e:
                logger.error(f"Error working on task {task['id']}: {e}")
                self.task_manager.fail_task(task['id'], error=str(e))

        return worked

    def _analyze_for_improvements(self) -> int:
        """Analyze codebase for improvement opportunities."""
        # This would spawn a subagent to analyze code
        # For now, just log that we would do this
        logger.info("Code analysis for improvements (placeholder)")

        # In full implementation:
        # 1. Spawn subagent to analyze a module
        # 2. Look for common issues (error handling, logging, etc.)
        # 3. Create proposals for fixes

        return 0  # Proposals created

    def _run_reflection(self) -> bool:
        """Run daily reflection."""
        logger.info("Running daily reflection...")

        # Get reflection agent (would be Sonnet)
        # For now, placeholder
        reflection_dir = self.config.reflections_dir
        reflection_dir.mkdir(parents=True, exist_ok=True)

        # Create reflection file
        date_str = datetime.now().strftime("%Y-%m-%d")
        reflection_path = reflection_dir / f"reflection-{date_str}.md"

        if reflection_path.exists():
            logger.info("Reflection already exists for today")
            return False

        # Would spawn reflection subagent here
        # For now, create placeholder
        reflection_path.write_text(f"""# Reflection - {date_str}

*This is a placeholder reflection. In full implementation, this would be generated by the reflection agent.*

## Today's Activities

- Nightshift cycle executed
- Tasks processed
- System operational

## Learnings

[To be filled by reflection agent]

## Tomorrow's Focus

[To be filled by reflection agent]
""")

        logger.info(f"Reflection saved: {reflection_path.name}")
        return True

    def _generate_briefing(self) -> bool:
        """Generate morning briefing."""
        logger.info("Generating morning briefing...")

        briefings_dir = self.config.entity_home / "briefings"
        briefings_dir.mkdir(parents=True, exist_ok=True)

        date_str = datetime.now().strftime("%Y-%m-%d")
        briefing_path = briefings_dir / f"briefing-{date_str}.md"

        if briefing_path.exists():
            logger.info("Briefing already exists for today")
            return False

        # Gather stats
        task_stats = self.task_manager.get_stats()
        pending_proposals = self.proposal_manager.list_proposals(status="pending")

        # Create briefing
        briefing = f"""# Morning Briefing - {date_str}

## Good Morning!

Here's what happened overnight and what's ahead today.

## Nightshift Summary

- **Tasks:** {task_stats.get('pending', 0)} pending, {task_stats.get('in_progress', 0)} in progress
- **Proposals:** {len(pending_proposals)} awaiting review
- **System:** Operational

## Pending Review

"""

        if pending_proposals:
            briefing += "### Proposals to Review\n\n"
            for p in pending_proposals[:5]:  # Top 5
                briefing += f"- **{p.title}** ({p.priority}) - `{p.id}`\n"
        else:
            briefing += "No proposals pending.\n"

        briefing += f"""

## Today's Focus

[Entity's suggested priorities would go here]

## Quick Stats

- Total tasks: {task_stats.get('total', 0)}
- Completed: {task_stats.get('completed', 0)}
- Active sessions: [count]

---

*Generated automatically during nightshift*
"""

        briefing_path.write_text(briefing)
        logger.info(f"Briefing saved: {briefing_path.name}")
        return True


# Global instance
_nightshift_manager: Optional[NightshiftManager] = None


def get_nightshift_manager(config: Optional[Config] = None) -> NightshiftManager:
    """Get or create the global nightshift manager."""
    global _nightshift_manager
    if _nightshift_manager is None:
        _nightshift_manager = NightshiftManager(config)
    return _nightshift_manager


def run_nightshift_cycle(config: Optional[Config] = None) -> Dict:
    """Run a nightshift cycle (for cron)."""
    manager = get_nightshift_manager(config)
    return manager.run_nightshift_cycle()
