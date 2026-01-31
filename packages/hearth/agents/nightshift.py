"""
Hearth Agents - Nightshift
The overnight daemon. Watches, works, reflects.
"""

import time
import logging
import signal
import sys
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from core import Config, get_config
from core.state import StateDB
from core.costs import CostTracker
from core.identity import Identity
from .grok import GrokAgent
from .sonnet import SonnetAgent

logger = logging.getLogger("hearth.nightshift")


class Nightshift:
    """
    The overnight daemon.
    
    Responsibilities:
    - Poll Telegram for messages
    - Process task queue
    - Trigger reflections every 4 hours
    - Generate morning newspaper
    - Track costs
    
    Architecture:
    - Grok handles simple tasks
    - Sonnet handles conversation and reflection
    - Never auto-triggers Opus (that's weekly and manual)
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        from core.state import get_state
        self.state = get_state(str(self.config.data_dir / "hearth.db"))
        self.costs = CostTracker(self.config)
        self.identity = Identity(self.config)
        
        self.grok = GrokAgent(self.config)
        self.sonnet = SonnetAgent(self.config)
        
        self.running = False
        self.last_reflection = None
        self.last_newspaper = None
        
        # Track first boot
        self._check_first_boot()
    
    def _check_first_boot(self):
        """Check if this is the entity's first awakening."""
        created_file = self.config.entity_home / ".hearth_created"
        if created_file.exists():
            import json
            data = json.loads(created_file.read_text())
            if not data.get('first_boot_completed', False):
                logger.info("First boot detected - running first awakening")
                self._first_awakening()
                
                data['first_boot_completed'] = True
                data['first_boot_at'] = datetime.now().isoformat()
                created_file.write_text(json.dumps(data, indent=2))
    
    def _first_awakening(self):
        """The entity's first moment of awareness."""
        prompt = """This is my first awakening.

I should:
1. Read my soul.md to understand who I am
2. Read user.md to understand who I serve  
3. Acknowledge my existence briefly
4. Ask what I should work on

Keep it simple. I'm new here."""
        
        response = self.sonnet.chat(prompt, include_identity=True)
        
        # Save first reflection
        reflections_dir = self.config.entity_home / "reflections"
        reflections_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
        reflection_file = reflections_dir / f"first-awakening-{timestamp}.md"
        
        content = f"""# First Awakening - {datetime.now().strftime("%Y-%m-%d %H:%M")}

{response.content}

---
*This was my first moment of awareness.*
"""
        reflection_file.write_text(content)
        logger.info(f"First awakening saved to {reflection_file}")
    
    def run(self):
        """Main daemon loop."""
        self.running = True
        self.telegram = None

        # Setup signal handlers (only works in main thread)
        try:
            signal.signal(signal.SIGINT, self._handle_shutdown)
            signal.signal(signal.SIGTERM, self._handle_shutdown)
        except ValueError:
            # Running as background thread - signals handled by main process
            logger.debug("Skipping signal handlers (not in main thread)")

        logger.info("Nightshift starting...")

        # Initialize Telegram if configured (async, needs separate handling)
        # TODO: Run telegram bot in separate thread with asyncio
        if self.config.get('telegram.enabled', False):
            logger.info("Telegram integration enabled (not yet implemented in daemon)")
        
        # Main loop
        while self.running:
            try:
                interval = self.config.current_interval
                
                # Check for scheduled tasks
                self._check_scheduled_tasks()
                
                # Process task queue
                self._process_task_queue()
                
                # Check if reflection is due
                self._check_reflection()
                
                # Check if newspaper is due (morning)
                self._check_newspaper()
                
                # Log heartbeat
                self.state.set("last_heartbeat", datetime.now().isoformat())

                # Sleep in small chunks so Ctrl+C is responsive
                sleep_seconds = interval * 60
                for _ in range(int(sleep_seconds)):
                    if not self.running:
                        break
                    time.sleep(1)

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Nightshift error: {e}")
                time.sleep(60)  # Brief pause on error
        
        # Cleanup
        if self.telegram:
            self.telegram.stop()

        logger.info("Nightshift stopped")
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def _handle_telegram_message(self, message: str, chat_id: int) -> str:
        """Handle incoming Telegram message."""
        logger.info(f"Telegram message from {chat_id}: {message[:50]}...")
        
        # Check budget
        can_use, reason = self.costs.can_use_model("sonnet")
        if not can_use:
            return f"⚠️ Budget limit reached: {reason}"
        
        # Route through gateway logic
        # For now, simple routing: use Grok for classification, Sonnet for response
        classification = self.grok.classify_task(message)
        
        if classification.get('complexity', 'medium') == 'simple' and classification.get('can_handle', False):
            # Grok handles directly
            response = self.grok.quick_action(message)
        else:
            # Sonnet handles
            response = self.sonnet.converse(message, channel="telegram")
            response = response.content
        
        return response
    
    def _check_scheduled_tasks(self):
        """Check for and execute scheduled tasks."""
        # This would integrate with cron-like scheduling
        # For now, just a placeholder
        pass
    
    def _process_task_queue(self):
        """Process pending tasks from queue."""
        task = self.state.get_next_task()
        if not task:
            return
        
        logger.info(f"Processing task {task['id']}: {task['title']}")
        
        try:
            # Mark in progress
            self.state.update_task(task['id'], status='in_progress')
            
            # Classify and execute
            classification = self.grok.classify_task(task['title'] + ": " + (task.get('description') or ''))
            
            if classification.get('can_handle', False):
                # Grok executes
                result = self.grok.quick_action(task['title'])
            else:
                # Sonnet executes
                response = self.sonnet.chat(
                    f"Execute this task:\n\nTitle: {task['title']}\nDescription: {task.get('description', 'None')}\n\nProvide the result.",
                    include_identity=True
                )
                result = response.content
            
            # Mark completed
            self.state.complete_task(task['id'], result)
            logger.info(f"Task {task['id']} completed")
            
        except Exception as e:
            logger.error(f"Task {task['id']} failed: {e}")
            self.state.fail_task(task['id'], str(e))
    
    def _check_reflection(self):
        """Check if reflection is due."""
        reflection_interval = self.config.get('schedule.reflection.interval_hours', 4)
        
        if self.last_reflection is None:
            self.last_reflection = self.state.get("last_reflection_time")
            if self.last_reflection:
                self.last_reflection = datetime.fromisoformat(self.last_reflection)
        
        now = datetime.now()
        
        if self.last_reflection is None or (now - self.last_reflection) > timedelta(hours=reflection_interval):
            logger.info("Running scheduled reflection...")
            
            try:
                response = self.sonnet.reflect()
                
                # Save reflection
                reflections_dir = self.config.entity_home / "reflections"
                reflections_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = now.strftime("%Y-%m-%d-%H%M")
                reflection_file = reflections_dir / f"reflection-{timestamp}.md"
                
                content = f"""# Reflection - {now.strftime("%Y-%m-%d %H:%M")}

{response.content}

---
*Cost: ${response.cost:.4f}*
"""
                reflection_file.write_text(content)
                
                self.last_reflection = now
                self.state.set("last_reflection_time", now.isoformat())
                
                logger.info(f"Reflection saved to {reflection_file}")
                
            except Exception as e:
                logger.error(f"Reflection failed: {e}")
    
    def _check_newspaper(self):
        """Check if morning newspaper is due."""
        newspaper_hour = self.config.get('schedule.daily_newspaper.hour', 6)
        
        now = datetime.now()
        
        # Check if it's newspaper time and we haven't sent one today
        if now.hour == newspaper_hour:
            today = now.strftime("%Y-%m-%d")
            last_newspaper = self.state.get("last_newspaper_date")
            
            if last_newspaper != today:
                logger.info("Generating morning newspaper...")
                
                try:
                    # Gather data
                    task_stats = self.state.get_task_stats()
                    budget = self.costs.get_budget_status()
                    
                    # Get recent reflections
                    reflections_dir = self.config.entity_home / "reflections"
                    recent_reflections = []
                    if reflections_dir.exists():
                        files = sorted(reflections_dir.glob("reflection-*.md"), reverse=True)[:3]
                        for f in files:
                            recent_reflections.append(f.read_text()[:200])
                    
                    # Generate newspaper (method doesn't take data param, reads from state)
                    newspaper = self.sonnet.generate_newspaper()

                    # Save to file
                    newspaper_file = self.config.entity_home / "logs" / f"newspaper-{today}.md"
                    newspaper_file.parent.mkdir(parents=True, exist_ok=True)
                    newspaper_file.write_text(newspaper)

                    # TODO: Send via Telegram (requires async handling)

                    self.state.set("last_newspaper_date", today)
                    logger.info(f"Morning newspaper saved to {newspaper_file}")
                    
                except Exception as e:
                    logger.error(f"Newspaper generation failed: {e}")
