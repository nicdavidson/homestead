from __future__ import annotations

import asyncio
import logging
import sys
import time
from pathlib import Path

from almanac.store import JobStore

log = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 30


class Scheduler:
    """Async scheduler that checks jobs and fires them on time."""

    def __init__(self, store: JobStore, homestead_dir: str = "~/.homestead") -> None:
        self._store = store
        self._homestead_dir = homestead_dir
        self._running = False
        self._outbox_db = str(
            Path(homestead_dir).expanduser() / "outbox.db"
        )

    async def run(self) -> None:
        """Main scheduler loop. Runs until stopped or cancelled."""
        self._running = True
        log.info(
            "Scheduler loop started (poll every %ds)", POLL_INTERVAL_SECONDS
        )

        # Log enabled jobs on startup
        try:
            enabled = self._store.list_jobs(enabled_only=True)
            log.info("Loaded %d enabled job(s)", len(enabled))
            for job in enabled:
                log.info(
                    "  - %s (%s / %s) next_run=%s",
                    job.name,
                    job.schedule.type.value if job.schedule else "?",
                    job.action.type if job.action else "?",
                    job.next_run_at,
                )
        except Exception:
            log.exception("Failed to load jobs on startup")

        while self._running:
            try:
                await self._tick()
            except asyncio.CancelledError:
                log.info("Scheduler cancelled")
                break
            except Exception:
                log.exception("Unexpected error in scheduler tick")

            try:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                log.info("Scheduler sleep cancelled")
                break

        log.info("Scheduler loop stopped")

    async def stop(self) -> None:
        self._running = False

    async def _tick(self) -> None:
        """One pass: find due jobs and execute them."""
        due_jobs = self._store.get_due_jobs()
        if not due_jobs:
            return

        log.info("Found %d due job(s)", len(due_jobs))

        for job in due_jobs:
            try:
                log.info("Executing job %s (%s)", job.name, job.id)
                await self._execute_action(job)
                self._store.mark_run(job.id)
                log.info("Job %s completed (run #%d)", job.name, job.run_count + 1)
            except Exception:
                log.exception("Job %s (%s) failed", job.name, job.id)
                # Still mark the run so next_run_at advances and we don't
                # retry the same failed job every 30 seconds forever.
                try:
                    self._store.mark_run(job.id)
                except Exception:
                    log.exception("Failed to mark_run for %s after error", job.id)

    async def _execute_action(self, job) -> None:
        """Dispatch to the appropriate action handler."""
        if job.action is None:
            log.warning("Job %s has no action configured", job.id)
            return

        action_type = job.action.type
        config = job.action.config

        if action_type == "outbox":
            await self._action_outbox(config)
        elif action_type == "command":
            await self._action_command(config)
        elif action_type == "webhook":
            await self._action_webhook(config)
        else:
            log.warning("Unknown action type %r for job %s", action_type, job.id)

    async def _action_outbox(self, config: dict) -> None:
        """Write a message to the shared outbox for herald to deliver."""
        chat_id = config.get("chat_id")
        agent_name = config.get("agent_name", "almanac")
        message = config.get("message", "")

        if not chat_id or not message:
            log.warning("Outbox action missing chat_id or message: %s", config)
            return

        # Import outbox from common package
        common_pkg = Path(__file__).resolve().parent.parent.parent / "common"
        if str(common_pkg) not in sys.path:
            sys.path.insert(0, str(common_pkg))

        from common.outbox import post_message

        post_message(
            db_path=self._outbox_db,
            chat_id=int(chat_id),
            agent_name=agent_name,
            message=message,
        )
        log.info("Posted outbox message to chat %s: %s", chat_id, message[:80])

    async def _action_command(self, config: dict) -> None:
        """Run a shell command via asyncio subprocess."""
        command = config.get("command", "")
        args = config.get("args", [])
        timeout = config.get("timeout", 60)

        if not command:
            log.warning("Command action has empty command")
            return

        cmd_parts = [command] + list(args)
        log.info("Running command: %s", " ".join(cmd_parts))

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )

            if proc.returncode == 0:
                log.info(
                    "Command succeeded (rc=0), stdout=%d bytes",
                    len(stdout) if stdout else 0,
                )
            else:
                log.warning(
                    "Command exited with code %d, stderr: %s",
                    proc.returncode,
                    (stderr or b"").decode(errors="replace")[:500],
                )
        except asyncio.TimeoutError:
            log.error("Command timed out after %ds: %s", timeout, command)
            try:
                proc.kill()
            except Exception:
                pass

    async def _action_webhook(self, config: dict) -> None:
        """Send an HTTP request to a URL."""
        url = config.get("url", "")
        method = config.get("method", "POST").upper()
        headers = config.get("headers", {})
        body = config.get("body", "")

        if not url:
            log.warning("Webhook action has empty URL")
            return

        log.info("Sending %s webhook to %s", method, url)

        try:
            import urllib.request
            import urllib.error

            data = body.encode("utf-8") if body else None
            req = urllib.request.Request(url, data=data, method=method)

            # Default content type for POST with body
            if data and "Content-Type" not in headers:
                req.add_header("Content-Type", "application/json")

            for key, value in headers.items():
                req.add_header(key, value)

            # Run the blocking call in a thread to avoid blocking the loop
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(req, timeout=30),
            )
            log.info(
                "Webhook response: %d %s",
                response.status,
                response.reason,
            )
        except urllib.error.HTTPError as exc:
            log.warning("Webhook HTTP error: %d %s", exc.code, exc.reason)
        except Exception:
            log.exception("Webhook request failed for %s", url)

    async def execute_job(self, job_id: str) -> bool:
        """Manually trigger a single job by ID. Returns True on success."""
        job = self._store.get(job_id)
        if job is None:
            return False

        try:
            await self._execute_action(job)
            self._store.mark_run(job.id)
            return True
        except Exception:
            log.exception("Manual execution of job %s failed", job_id)
            return False
