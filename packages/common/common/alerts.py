"""Alert engine — watches Watchtower logs and fires notifications on anomalies.

Rules are stored in SQLite alongside alert history to support dedup and cooldowns.
Designed to be called periodically by Almanac's scheduler.

Supports auto-resolution (notifies when a previously-firing rule clears),
process health checks (PID file monitoring), and circuit breakers
(suppresses alerts after N consecutive fires).
"""

from __future__ import annotations

import json
import logging
import os
import signal
import time
from dataclasses import dataclass, field
from pathlib import Path

from common.db import get_connection
from common.outbox import post_message

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_CREATE_RULES_TABLE = """\
CREATE TABLE IF NOT EXISTS alert_rules (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT DEFAULT '',
    rule_type   TEXT NOT NULL,
    config_json TEXT NOT NULL DEFAULT '{}',
    enabled     INTEGER DEFAULT 1,
    cooldown_s  INTEGER DEFAULT 900,
    created_at  REAL NOT NULL
)
"""

_CREATE_HISTORY_TABLE = """\
CREATE TABLE IF NOT EXISTS alert_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id    TEXT NOT NULL,
    fired_at   REAL NOT NULL,
    message    TEXT NOT NULL,
    resolved   INTEGER DEFAULT 0,
    resolved_at REAL
)
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_alert_history_rule ON alert_history (rule_id, fired_at)",
    "CREATE INDEX IF NOT EXISTS idx_alert_rules_enabled ON alert_rules (enabled)",
]

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclass
class AlertRule:
    id: str
    name: str
    description: str
    rule_type: str  # error_spike, service_down, disk_space, custom_query
    config: dict
    enabled: bool
    cooldown_s: int
    created_at: float


@dataclass
class AlertEvent:
    id: int
    rule_id: str
    fired_at: float
    message: str
    resolved: bool
    resolved_at: float | None


# ---------------------------------------------------------------------------
# Default rules
# ---------------------------------------------------------------------------

DEFAULT_RULES: list[dict] = [
    {
        "id": "error_spike_herald",
        "name": "Herald Error Spike",
        "description": "Alert when Herald logs >5 errors in 15 minutes",
        "rule_type": "error_spike",
        "config": {"source": "herald", "threshold": 5, "window_minutes": 15},
        "cooldown_s": 1800,
    },
    {
        "id": "error_spike_manor",
        "name": "Manor Error Spike",
        "description": "Alert when Manor logs >5 errors in 15 minutes",
        "rule_type": "error_spike",
        "config": {"source": "manor", "threshold": 5, "window_minutes": 15},
        "cooldown_s": 1800,
    },
    {
        "id": "error_spike_almanac",
        "name": "Almanac Error Spike",
        "description": "Alert when Almanac logs >3 errors in 15 minutes",
        "rule_type": "error_spike",
        "config": {"source": "almanac", "threshold": 3, "window_minutes": 15},
        "cooldown_s": 1800,
    },
    {
        "id": "service_down_manor",
        "name": "Manor API Down",
        "description": "Alert when Manor API health endpoint is unreachable",
        "rule_type": "service_down",
        "config": {"url": "http://localhost:8700/health", "timeout": 5},
        "cooldown_s": 300,
    },
    {
        "id": "disk_space_low",
        "name": "Low Disk Space",
        "description": "Alert when ~/.homestead/ exceeds 500MB",
        "rule_type": "disk_space",
        "config": {"path": "~/.homestead", "max_mb": 500},
        "cooldown_s": 3600,
    },
    {
        "id": "process_herald",
        "name": "Herald Process Down",
        "description": "Alert when Herald process is not running (via PID file)",
        "rule_type": "process_check",
        "config": {
            "pid_file": "~/.homestead/herald.pid",
            "service_name": "Herald",
        },
        "cooldown_s": 300,
    },
]

# Maximum consecutive fires before suppressing notifications (circuit breaker).
# The rule still records history, but TG messages stop until resolved.
CIRCUIT_BREAKER_THRESHOLD = 5

# ---------------------------------------------------------------------------
# Alert Engine
# ---------------------------------------------------------------------------


class AlertEngine:
    """Evaluates alert rules against Watchtower logs and fires notifications."""

    def __init__(
        self,
        alerts_db: str | Path,
        watchtower_db: str | Path,
        outbox_db: str | Path,
        chat_id: int,
    ) -> None:
        self._alerts_db = Path(alerts_db).expanduser()
        self._watchtower_db = Path(watchtower_db).expanduser()
        self._outbox_db = str(Path(outbox_db).expanduser())
        self._chat_id = chat_id
        self._ensure_schema()

    def _get_conn(self):
        return get_connection(self._alerts_db)

    def _ensure_schema(self) -> None:
        conn = self._get_conn()
        conn.execute(_CREATE_RULES_TABLE)
        conn.execute(_CREATE_HISTORY_TABLE)
        for idx in _CREATE_INDEXES:
            conn.execute(idx)
        conn.commit()
        # Seed default rules if table is empty
        count = conn.execute("SELECT COUNT(*) as c FROM alert_rules").fetchone()["c"]
        if count == 0:
            self._seed_defaults(conn)
        conn.close()

    def _seed_defaults(self, conn) -> None:
        now = time.time()
        for rule in DEFAULT_RULES:
            conn.execute(
                "INSERT OR IGNORE INTO alert_rules "
                "(id, name, description, rule_type, config_json, enabled, cooldown_s, created_at) "
                "VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
                (
                    rule["id"],
                    rule["name"],
                    rule.get("description", ""),
                    rule["rule_type"],
                    json.dumps(rule["config"]),
                    rule.get("cooldown_s", 900),
                    now,
                ),
            )
        conn.commit()
        log.info("Seeded %d default alert rules", len(DEFAULT_RULES))

    # -- Rule CRUD ----------------------------------------------------------

    def list_rules(self) -> list[AlertRule]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM alert_rules ORDER BY created_at"
        ).fetchall()
        conn.close()
        return [self._row_to_rule(r) for r in rows]

    def get_rule(self, rule_id: str) -> AlertRule | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM alert_rules WHERE id = ?", (rule_id,)
        ).fetchone()
        conn.close()
        return self._row_to_rule(row) if row else None

    def upsert_rule(self, rule: dict) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO alert_rules "
            "(id, name, description, rule_type, config_json, enabled, cooldown_s, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                rule["id"],
                rule["name"],
                rule.get("description", ""),
                rule["rule_type"],
                json.dumps(rule.get("config", {})),
                1 if rule.get("enabled", True) else 0,
                rule.get("cooldown_s", 900),
                rule.get("created_at", time.time()),
            ),
        )
        conn.commit()
        conn.close()

    def toggle_rule(self, rule_id: str) -> bool:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT enabled FROM alert_rules WHERE id = ?", (rule_id,)
        ).fetchone()
        if row is None:
            conn.close()
            return False
        new_val = 0 if row["enabled"] else 1
        conn.execute(
            "UPDATE alert_rules SET enabled = ? WHERE id = ?", (new_val, rule_id)
        )
        conn.commit()
        conn.close()
        return True

    def delete_rule(self, rule_id: str) -> bool:
        conn = self._get_conn()
        conn.execute("DELETE FROM alert_rules WHERE id = ?", (rule_id,))
        conn.commit()
        affected = conn.total_changes
        conn.close()
        return affected > 0

    # -- History ------------------------------------------------------------

    def list_history(self, limit: int = 50) -> list[AlertEvent]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM alert_history ORDER BY fired_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [self._row_to_event(r) for r in rows]

    # -- Evaluation ---------------------------------------------------------

    def check_all(self) -> list[str]:
        """Evaluate all enabled rules. Returns list of alert messages fired."""
        conn = self._get_conn()
        rules = conn.execute(
            "SELECT * FROM alert_rules WHERE enabled = 1"
        ).fetchall()
        conn.close()

        fired: list[str] = []
        for row in rules:
            rule = self._row_to_rule(row)
            try:
                msg = self._evaluate_rule(rule)
                if msg:
                    # Circuit breaker: suppress TG after N consecutive fires
                    consecutive = self._consecutive_fires(rule)
                    if consecutive >= CIRCUIT_BREAKER_THRESHOLD:
                        log.debug(
                            "Rule %s circuit-breaker active (%d consecutive), recording only",
                            rule.id, consecutive,
                        )
                        self._record_history(rule, msg)
                        continue
                    if self._in_cooldown(rule):
                        log.debug("Rule %s in cooldown, skipping", rule.id)
                        continue
                    self._fire_alert(rule, msg)
                    fired.append(msg)
                else:
                    # Rule passed — auto-resolve any unresolved alerts
                    self._maybe_resolve(rule)
            except Exception:
                log.exception("Error evaluating rule %s", rule.id)

        return fired

    def _evaluate_rule(self, rule: AlertRule) -> str | None:
        """Evaluate a single rule. Returns alert message or None."""
        if rule.rule_type == "error_spike":
            return self._check_error_spike(rule)
        elif rule.rule_type == "service_down":
            return self._check_service_down(rule)
        elif rule.rule_type == "disk_space":
            return self._check_disk_space(rule)
        elif rule.rule_type == "custom_query":
            return self._check_custom_query(rule)
        elif rule.rule_type == "process_check":
            return self._check_process(rule)
        else:
            log.warning("Unknown rule type: %s", rule.rule_type)
            return None

    def _check_error_spike(self, rule: AlertRule) -> str | None:
        source = rule.config.get("source", "")
        threshold = rule.config.get("threshold", 5)
        window_min = rule.config.get("window_minutes", 15)
        since = time.time() - window_min * 60

        if not self._watchtower_db.is_file():
            return None

        conn = get_connection(self._watchtower_db)
        try:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM logs "
                "WHERE level IN ('ERROR', 'CRITICAL') "
                "AND source LIKE ? AND timestamp >= ?",
                (f"{source}%", since),
            ).fetchone()
            count = row["cnt"] if row else 0
        except Exception:
            return None
        finally:
            conn.close()

        if count >= threshold:
            return (
                f"{rule.name}: {count} errors from {source} "
                f"in the last {window_min} minutes (threshold: {threshold})"
            )
        return None

    def _check_service_down(self, rule: AlertRule) -> str | None:
        url = rule.config.get("url", "")
        timeout = rule.config.get("timeout", 5)
        if not url:
            return None

        try:
            import urllib.request
            req = urllib.request.Request(url, method="GET")
            urllib.request.urlopen(req, timeout=timeout)
            return None  # Service is up
        except Exception as exc:
            return f"{rule.name}: {url} unreachable ({exc})"

    def _check_disk_space(self, rule: AlertRule) -> str | None:
        path = Path(rule.config.get("path", "~/.homestead")).expanduser()
        max_mb = rule.config.get("max_mb", 500)
        if not path.is_dir():
            return None

        total_bytes = sum(
            f.stat().st_size for f in path.rglob("*") if f.is_file()
        )
        total_mb = total_bytes / (1024 * 1024)

        if total_mb > max_mb:
            return (
                f"{rule.name}: {path} is {total_mb:.0f}MB "
                f"(limit: {max_mb}MB)"
            )
        return None

    def _check_custom_query(self, rule: AlertRule) -> str | None:
        """Run a custom SQL query against watchtower and alert if rows returned."""
        query = rule.config.get("query", "")
        if not query or not self._watchtower_db.is_file():
            return None

        conn = get_connection(self._watchtower_db)
        try:
            rows = conn.execute(query).fetchall()
            if rows:
                return f"{rule.name}: custom query returned {len(rows)} row(s)"
            return None
        except Exception:
            log.warning("Custom query failed for rule %s", rule.id)
            return None
        finally:
            conn.close()

    def _check_process(self, rule: AlertRule) -> str | None:
        """Check if a process is alive via its PID file."""
        pid_file = Path(rule.config.get("pid_file", "")).expanduser()
        service_name = rule.config.get("service_name", "Unknown")

        if not pid_file.is_file():
            return f"{rule.name}: PID file {pid_file} does not exist — {service_name} likely not running"

        try:
            pid_str = pid_file.read_text().strip()
            pid = int(pid_str)
        except (ValueError, OSError):
            return f"{rule.name}: Could not read PID from {pid_file}"

        try:
            os.kill(pid, 0)  # signal 0 = check if process exists
            return None  # Process is alive
        except ProcessLookupError:
            return f"{rule.name}: {service_name} process (PID {pid}) is not running"
        except PermissionError:
            return None  # Process exists but we lack permission (still alive)

    def _consecutive_fires(self, rule: AlertRule) -> int:
        """Count consecutive unresolved fires for a rule (for circuit breaker)."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT resolved FROM alert_history WHERE rule_id = ? "
            "ORDER BY fired_at DESC LIMIT ?",
            (rule.id, CIRCUIT_BREAKER_THRESHOLD + 1),
        ).fetchall()
        conn.close()
        count = 0
        for r in rows:
            if r["resolved"]:
                break
            count += 1
        return count

    def _record_history(self, rule: AlertRule, message: str) -> None:
        """Record an alert in history without sending a notification."""
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO alert_history (rule_id, fired_at, message) VALUES (?, ?, ?)",
            (rule.id, time.time(), message),
        )
        conn.commit()
        conn.close()

    def _maybe_resolve(self, rule: AlertRule) -> None:
        """Auto-resolve unresolved alerts for a rule and send recovery notification."""
        conn = self._get_conn()
        unresolved = conn.execute(
            "SELECT id, message FROM alert_history "
            "WHERE rule_id = ? AND resolved = 0 "
            "ORDER BY fired_at DESC",
            (rule.id,),
        ).fetchall()

        if not unresolved:
            conn.close()
            return

        now = time.time()
        conn.execute(
            "UPDATE alert_history SET resolved = 1, resolved_at = ? "
            "WHERE rule_id = ? AND resolved = 0",
            (now, rule.id),
        )
        conn.commit()
        conn.close()

        # Send recovery notification
        tg_message = (
            f"<b>Resolved: {rule.name}</b>\n\n"
            f"Previously: {unresolved[0]['message']}\n"
            f"Resolved after {len(unresolved)} alert(s)."
        )
        post_message(
            db_path=self._outbox_db,
            chat_id=self._chat_id,
            agent_name="Watchtower",
            message=tg_message,
        )
        log.info("Auto-resolved %d alert(s) for rule %s", len(unresolved), rule.id)

    def _in_cooldown(self, rule: AlertRule) -> bool:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT MAX(fired_at) as last_fired FROM alert_history WHERE rule_id = ?",
            (rule.id,),
        ).fetchone()
        conn.close()
        if row and row["last_fired"]:
            return (time.time() - row["last_fired"]) < rule.cooldown_s
        return False

    def _fire_alert(self, rule: AlertRule, message: str) -> None:
        now = time.time()

        # Record in history
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO alert_history (rule_id, fired_at, message) VALUES (?, ?, ?)",
            (rule.id, now, message),
        )
        conn.commit()
        conn.close()

        # Send to Telegram via outbox
        tg_message = f"<b>Alert: {rule.name}</b>\n\n{message}"
        post_message(
            db_path=self._outbox_db,
            chat_id=self._chat_id,
            agent_name="Watchtower",
            message=tg_message,
        )
        log.warning("Alert fired: %s — %s", rule.name, message)

    # -- Helpers ------------------------------------------------------------

    @staticmethod
    def _row_to_rule(row) -> AlertRule:
        return AlertRule(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            rule_type=row["rule_type"],
            config=json.loads(row["config_json"]) if row["config_json"] else {},
            enabled=bool(row["enabled"]),
            cooldown_s=row["cooldown_s"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_event(row) -> AlertEvent:
        return AlertEvent(
            id=row["id"],
            rule_id=row["rule_id"],
            fired_at=row["fired_at"],
            message=row["message"],
            resolved=bool(row["resolved"]),
            resolved_at=row["resolved_at"],
        )
