#!/usr/bin/env bash
# Seed sample data into homestead databases for development/demo
set -euo pipefail

HOMESTEAD_DIR="${HOMESTEAD_DATA_DIR:-$HOME/.homestead}"

echo "Seeding sample data into $HOMESTEAD_DIR..."

# Seed some tasks
TASKS_DB="$HOMESTEAD_DIR/steward/tasks.db"
mkdir -p "$(dirname "$TASKS_DB")"
sqlite3 "$TASKS_DB" <<'SQL'
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending', priority TEXT NOT NULL DEFAULT 'normal',
    assignee TEXT DEFAULT 'auto', blockers_json TEXT DEFAULT '[]',
    depends_on_json TEXT DEFAULT '[]', created_at REAL NOT NULL,
    updated_at REAL NOT NULL, completed_at REAL, tags_json TEXT DEFAULT '[]',
    notes_json TEXT DEFAULT '[]', source TEXT DEFAULT ''
);

INSERT OR IGNORE INTO tasks VALUES
    ('seed-001', 'Set up CI/CD pipeline', 'Configure GitHub Actions for testing and deployment', 'pending', 'high', 'auto', '[]', '[]', strftime('%s','now'), strftime('%s','now'), NULL, '["devops","ci"]', '[]', 'steward'),
    ('seed-002', 'Write integration tests', 'End-to-end tests for herald message flow', 'in_progress', 'normal', 'auto', '[]', '[]', strftime('%s','now')-3600, strftime('%s','now'), NULL, '["testing","herald"]', '["Started with session lifecycle tests"]', 'steward'),
    ('seed-003', 'Add Slack integration', 'Support Slack as alternative to Telegram', 'pending', 'normal', 'auto', '[]', '[]', strftime('%s','now')-7200, strftime('%s','now')-7200, NULL, '["herald","integration"]', '[]', 'herald'),
    ('seed-004', 'Implement weekly synthesis', 'Almanac job for weekly reflection using Opus', 'blocked', 'normal', 'auto', '[{"type":"dependency","description":"Almanac scheduler needs to be running"}]', '[]', strftime('%s','now')-86400, strftime('%s','now')-86400, NULL, '["almanac","reflection"]', '[]', 'almanac'),
    ('seed-005', 'Document API endpoints', 'OpenAPI docs for Manor API', 'completed', 'low', 'auto', '[]', '[]', strftime('%s','now')-172800, strftime('%s','now')-3600, strftime('%s','now')-3600, '["docs","manor"]', '["Auto-generated from FastAPI"]', 'steward');
SQL

# Seed some scheduled jobs
JOBS_DB="$HOMESTEAD_DIR/almanac/jobs.db"
mkdir -p "$(dirname "$JOBS_DB")"
sqlite3 "$JOBS_DB" <<'SQL'
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT DEFAULT '',
    schedule_type TEXT NOT NULL, schedule_value TEXT NOT NULL,
    action_type TEXT NOT NULL, action_config_json TEXT NOT NULL,
    enabled INTEGER DEFAULT 1, last_run_at REAL, next_run_at REAL,
    run_count INTEGER DEFAULT 0, created_at REAL NOT NULL,
    tags_json TEXT DEFAULT '[]', source TEXT DEFAULT 'almanac'
);

INSERT OR IGNORE INTO jobs VALUES
    ('job-001', 'Morning Briefing', 'Daily morning summary', 'cron', '0 6 * * *', 'outbox', '{"chat_id":0,"agent_name":"almanac","message":"Good morning! Here is your daily briefing..."}', 1, NULL, strftime('%s','now')+3600, 0, strftime('%s','now'), '["daily","briefing"]', 'almanac'),
    ('job-002', 'Health Check', 'Periodic system health check', 'interval', '3600', 'command', '{"command":"echo","args":["health check ok"],"timeout":30}', 1, strftime('%s','now')-1800, strftime('%s','now')+1800, 12, strftime('%s','now')-86400, '["monitoring"]', 'almanac'),
    ('job-003', 'Weekly Synthesis', 'Deep weekly reflection', 'cron', '0 2 * * 0', 'outbox', '{"chat_id":0,"agent_name":"nightshift","message":"Starting weekly synthesis..."}', 0, NULL, NULL, 0, strftime('%s','now'), '["reflection","weekly"]', 'almanac');
SQL

# Seed some watchtower logs
WT_DB="$HOMESTEAD_DIR/watchtower.db"
sqlite3 "$WT_DB" <<'SQL'
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL NOT NULL,
    level TEXT NOT NULL, source TEXT NOT NULL, message TEXT NOT NULL,
    data_json TEXT, session_id TEXT, chat_id INTEGER
);

INSERT INTO logs (timestamp, level, source, message) VALUES
    (strftime('%s','now')-300, 'INFO', 'herald.main', 'Herald started successfully'),
    (strftime('%s','now')-240, 'INFO', 'herald.bot', 'Processing message from user'),
    (strftime('%s','now')-200, 'INFO', 'herald.providers', 'Dispatching to claude CLI'),
    (strftime('%s','now')-180, 'WARNING', 'herald.claude', 'Claude response took 45s'),
    (strftime('%s','now')-120, 'INFO', 'herald.bot', 'Response delivered (1234 chars)'),
    (strftime('%s','now')-60, 'ERROR', 'almanac.scheduler', 'Failed to execute job: connection timeout'),
    (strftime('%s','now')-30, 'INFO', 'herald.bot', 'Outbox: delivered nightshift message');
SQL

# Seed outbox message
OUTBOX_DB="$HOMESTEAD_DIR/outbox.db"
sqlite3 "$OUTBOX_DB" <<'SQL'
CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL,
    agent_name TEXT NOT NULL, message TEXT NOT NULL,
    parse_mode TEXT DEFAULT 'HTML', created_at REAL NOT NULL,
    sent_at REAL, status TEXT DEFAULT 'pending'
);

INSERT INTO outbox (chat_id, agent_name, message, created_at, sent_at, status) VALUES
    (0, 'nightshift', 'Completed overnight task: code review for PR #42', strftime('%s','now')-7200, strftime('%s','now')-7190, 'sent'),
    (0, 'almanac', 'Morning briefing ready', strftime('%s','now')-3600, strftime('%s','now')-3595, 'sent');
SQL

echo "Done! Seeded: 5 tasks, 3 jobs, 7 log entries, 2 outbox messages"
