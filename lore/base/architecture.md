# Homestead Architecture

Complete architectural mapping of the Homestead ecosystem.

## Package Overview

**Common** - Shared infrastructure (Watchtower logging, Outbox messaging, EventBus, Skills, Alerts)
**Herald** - Telegram bot interface with session management and Claude CLI integration
**Manor** - Web dashboard (FastAPI + Next.js) providing unified UI for all services
**Steward** - Task management with blocker modeling and dependency graphs
**Almanac** - Job scheduling (cron, interval, one-time) with action execution and alert monitoring
**MCP-Homestead** - Model Context Protocol server exposing homestead as Claude tools

## Data Architecture

All data stored under `~/.homestead/`:
- `watchtower.db` - Structured event logs from all packages
- `outbox.db` - Pending Telegram messages queue
- `alerts.db` - Alert rules and firing history
- `events.db` - Event bus pub/sub history
- `steward/tasks.db` - Task store
- `almanac/jobs.db` - Scheduled jobs
- `usage.db` - Token usage tracking
- `skills/` - Markdown skill library
- `scratchpad/` - Persistent AI memory files

Identity files in repo `lore/` directory (soul.md, claude.md, triggers.md, etc.)

## Communication Patterns

1. **Shared Database** - Direct SQLite access for structured data
2. **Event Bus** - Pub/sub for loose coupling between packages
3. **Filesystem** - Content sharing (skills, lore, scratchpad)
4. **HTTP API** - Manor as central API server
5. **Outbox Queue** - Async Telegram delivery pattern

## Key Flows

**User Message via Telegram:**
Telegram -> Herald -> Auth -> Session Load -> Claude CLI (with MCP tools) -> Stream Response -> Log to Watchtower -> Update Session

**Scheduled Job:**
Almanac polls -> Job due -> Execute action -> Notify via Outbox -> Herald sends to Telegram

**Alert Check:**
Almanac timer -> AlertEngine.check_all() -> Evaluate rules against Watchtower -> Auto-restart if needed -> Fire alert via Outbox -> Auto-resolve when cleared

**MCP Tool Call:**
Claude CLI -> MCP Request -> mcp-homestead server -> Manor API -> Database/Files -> Response

## Self-Correction Pipeline

1. **Logging**: All services log WARNING+ to Watchtower DB
2. **Alert Rules**: Error spikes, service health, disk space, process checks
3. **Auto-Restart**: Almanac detects downed Herald -> import check -> restart
4. **Auto-Resolution**: When rule clears, marks alerts resolved + sends recovery notification
5. **Circuit Breaker**: Suppresses TG after 5 consecutive fires (prevents storms)

## Technology Stack

- **AI**: Claude CLI, Claude API
- **Chat**: aiogram 3 (Telegram)
- **Web**: Next.js 15, React 19, FastAPI
- **Storage**: SQLite (WAL mode), Markdown files
- **IPC**: JSON-RPC (MCP), REST (HTTP), SQLite
