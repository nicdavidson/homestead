# Homestead Architecture

Complete architectural mapping of the Homestead ecosystem, documenting how all packages integrate and communicate.

## Package Overview

**Common** - Shared infrastructure (Watchtower logging, Outbox messaging, EventBus, Skills, Models)
**Herald** - Telegram bot interface with session management and Claude CLI integration
**Manor** - Web dashboard (FastAPI + Next.js) providing unified UI for all Homestead services
**Steward** - Task management with blocker modeling and dependency graphs
**Almanac** - Job scheduling (cron, interval, one-time) with action execution
**Cronicle** - Memory indexing and full-text search across lore, scratchpad, and journal
**MCP-Homestead** - Model Context Protocol server exposing Homestead as Claude tools

## Data Architecture

All runtime data stored under `~/.homestead/`:
- `watchtower.db` - Structured event logs from all packages
- `outbox.db` - Pending Telegram messages queue
- `events.db` - Event bus pub/sub history
- `memory.db` - Cronicle full-text search index
- `proposals.db` - Code/lore change proposals
- `usage.db` - Token usage tracking
- `steward/tasks.db` - Task store
- `almanac/jobs.db` - Scheduled jobs
- `skills/` - Markdown skill library
- `scratchpad/` - Persistent AI working memory
- `journal/` - Daily AI reflections and learnings

Identity files in repo `lore/` directory with layered overrides:
- `lore/base/` - Framework defaults (git-tracked, updated from upstream)
- `lore/` - User overrides (gitignored, personal customizations)

## Communication Patterns

1. **Shared Database** - Direct SQLite access for structured data
2. **Event Bus** - Pub/sub for loose coupling between packages
3. **Filesystem** - Content sharing (skills, lore, scratchpad, journal)
4. **HTTP API** - Manor as central API server
5. **Outbox Queue** - Async Telegram delivery pattern
6. **MCP Protocol** - Claude CLI tool interface

## Key Flows

**User Message via Telegram:**
Telegram -> Herald -> Auth -> Session Load -> Claude CLI (with MCP tools) -> Stream Response -> Log to Watchtower -> Update Session

**Auto-Context Injection:**
User message -> Cronicle search -> Relevant context prepended to prompt -> Claude sees enriched context

**Scheduled Job:**
Almanac polls -> Job due -> Execute action -> Create in Steward / post to Outbox -> Herald delivers

**MCP Tool Call:**
Claude CLI -> MCP Request -> mcp-homestead server -> Manor API -> Database/Files -> Response -> Claude

**Self-Improvement Loop:**
Conversation ends -> Reflection hook -> Journal entry -> Memory indexed -> Future queries enriched

**Lore Evolution:**
AI proposes change -> Proposal created -> Human reviews in Manor -> Approved -> Git commit -> History tracked

## Dependency Graph

```
lore/ (identity files, layered: base + user overrides)
    |
common (infrastructure)
    |-- herald (Telegram)
    |-- steward (tasks)
    |-- almanac (jobs)
    |
manor (web UI + API) <-- mcp-homestead (Claude tools)
    |
cronicle (memory index, auto-context)
```

## Technology Stack

- **AI**: Claude CLI, xAI Grok API
- **Chat**: aiogram 3 (Telegram)
- **Web**: Next.js 15, React 19, FastAPI
- **Storage**: SQLite (WAL mode), FTS5 full-text search, Markdown files
- **IPC**: JSON-RPC (MCP), REST (HTTP), SQLite
- **Version Control**: Git-backed proposals for auditable evolution

## Design Principles

- Decentralized data ownership (each package has own DB)
- Asynchronous message passing (EventBus, Outbox)
- Filesystem as content management (skills, lore, memory)
- Layered configuration (base defaults + user overrides)
- Structured logging (Watchtower)
- Multi-model support with session-based switching
- Git-backed audit trail for all changes
- Single-instance guarantees (PID locks)
