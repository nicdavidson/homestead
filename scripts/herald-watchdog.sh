#!/usr/bin/env bash
#
# herald-watchdog.sh — Monitor and auto-restart Herald
#
# Run via cron every minute:
#   * * * * * /path/to/homestead/scripts/herald-watchdog.sh
#
# What it does:
#   1. Check if Herald is running (via PID file lock)
#   2. If down, attempt restart
#   3. If restart fails, log to watchtower + drop an outbox message
#   4. On successful restart, log it
#

set -euo pipefail

HOMESTEAD_DIR="${HOMESTEAD_DATA_DIR:-$HOME/.homestead}"
HERALD_DIR="$(cd "$(dirname "$0")/../packages/herald" && pwd)"
HERALD_VENV="$HERALD_DIR/.venv"
HERALD_PID_FILE="$HOMESTEAD_DIR/herald.pid"
LOG_FILE="$HOMESTEAD_DIR/herald-watchdog.log"
MAX_LOG_LINES=500

# Watchtower DB for structured logging
WATCHTOWER_DB="$HOMESTEAD_DIR/watchtower.db"
OUTBOX_DB="$HOMESTEAD_DIR/outbox.db"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log() {
    local ts
    ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "$ts [watchdog] $*" >> "$LOG_FILE"
    # Rotate log file
    if [ "$(wc -l < "$LOG_FILE" 2>/dev/null || echo 0)" -gt "$MAX_LOG_LINES" ]; then
        tail -n 200 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"
    fi
}

log_to_watchtower() {
    local level="$1" message="$2"
    if [ -f "$WATCHTOWER_DB" ]; then
        sqlite3 "$WATCHTOWER_DB" "INSERT INTO logs (id, timestamp, level, source, message) VALUES (lower(hex(randomblob(16))), $(date +%s.%N), '$level', 'herald.watchdog', '$(echo "$message" | sed "s/'/''/g")');" 2>/dev/null || true
    fi
}

send_outbox_message() {
    local message="$1"
    if [ -f "$OUTBOX_DB" ]; then
        sqlite3 "$OUTBOX_DB" "INSERT INTO outbox (id, agent_name, message, channel, status, created_at) VALUES (lower(hex(randomblob(16))), 'watchdog', '$(echo "$message" | sed "s/'/''/g")', 'telegram', 'pending', $(date +%s.%N));" 2>/dev/null || true
    fi
}

is_herald_running() {
    # Check PID file + verify process is alive
    if [ ! -f "$HERALD_PID_FILE" ]; then
        return 1
    fi
    local pid
    pid="$(cat "$HERALD_PID_FILE" 2>/dev/null | tr -d '[:space:]')"
    if [ -z "$pid" ]; then
        return 1
    fi
    if kill -0 "$pid" 2>/dev/null; then
        return 0
    fi
    return 1
}

start_herald() {
    cd "$HERALD_DIR"
    if [ ! -d "$HERALD_VENV" ]; then
        log "ERROR: Herald venv not found at $HERALD_VENV"
        return 1
    fi

    # Run tests first — don't restart a broken Herald
    log "Running Herald import checks..."
    if ! "$HERALD_VENV/bin/python" -c "from herald.bot import create_bot; from herald.claude import spawn_claude; print('ok')" 2>/dev/null; then
        log "ERROR: Herald import check failed — code may be corrupted"
        log_to_watchtower "ERROR" "Herald import check failed — not restarting (code may be corrupted)"
        send_outbox_message "Herald is down and won't restart — import check failed. Code may be corrupted. Check bot.py."
        return 1
    fi

    # Start Herald in the background
    log "Starting Herald..."
    nohup "$HERALD_VENV/bin/python" -m herald.main >> "$HOMESTEAD_DIR/herald-stdout.log" 2>&1 &
    local new_pid=$!

    # Wait a moment and check it's still alive
    sleep 2
    if kill -0 "$new_pid" 2>/dev/null; then
        log "Herald started successfully (PID $new_pid)"
        log_to_watchtower "INFO" "Herald restarted by watchdog (PID $new_pid)"
        send_outbox_message "Herald was down — watchdog restarted it (PID $new_pid)"
        return 0
    else
        log "ERROR: Herald started but died immediately"
        log_to_watchtower "ERROR" "Herald failed to start — process died immediately"
        send_outbox_message "Herald is down — watchdog tried to restart but it died immediately. Check logs."
        return 1
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

mkdir -p "$HOMESTEAD_DIR"

if is_herald_running; then
    # Herald is alive — nothing to do
    exit 0
fi

# Herald is down
log "Herald is not running — attempting restart"
log_to_watchtower "WARNING" "Herald is down — watchdog attempting restart"

# Clean stale PID file
rm -f "$HERALD_PID_FILE"

if start_herald; then
    exit 0
else
    log "Failed to restart Herald"
    exit 1
fi
