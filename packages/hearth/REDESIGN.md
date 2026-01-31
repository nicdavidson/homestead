# Hearth Redesign Proposal

**Date:** 2026-01-31
**Status:** Draft
**Author:** Analysis of existing codebase for homestead monorepo integration

---

## 1. Current Architecture Summary

Hearth is a standalone AI entity framework built as a single-process Python application. It was designed to run autonomously on a dedicated machine (or VM), with the AI entity having its own system user, home directory, and persistent state.

### Core Components

| Component | File(s) | Purpose |
|-----------|---------|---------|
| **Identity** | `core/identity.py` | soul.md, user.md, system prompts, naming ceremony, soul edits |
| **State** | `core/state.py` | SQLite-backed storage: tasks, conversations, sessions, costs, KV store |
| **Tasks** | `core/tasks.py` | Task CRUD, priority queue, status tracking |
| **Projects** | `core/projects.py` | Multi-day project management (JSON + markdown files) |
| **Skills** | `core/skills.py` | Learned skill library (markdown files), search, tagging |
| **Reflections** | `core/reflections.py` | Daily reflections, weekly synthesis, naming ceremony |
| **Proposals** | `core/proposals.py` | Self-improvement code proposals with diff, review, apply, git commit |
| **Sessions** | `core/sessions.py` | Subagent spawning, ThreadPoolExecutor, announce-back pattern |
| **Costs** | `core/costs.py` | API budget tracking, per-model spending, budget enforcement |
| **Router** | `core/router.py` | Intent classification via regex, model tier routing (deprecated) |
| **Nightshift** | `core/nightshift.py` | Autonomous nightshift cycle: tasks, reflection, self-improvement, briefings |
| **API** | `core/api.py` | FastAPI REST API (18+ endpoints), WebSocket manager |
| **Tools** | `core/tools.py` | Tool definitions for agent spawning (spawn_agent, list_subagents) |
| **Config** | `core/config.py` | YAML config loader, env resolution, schedule logic |

### Agent Layer

| Agent | File(s) | Purpose |
|-------|---------|---------|
| **BaseAgent** | `agents/base.py` | Abstract base: chat, reflect, cost logging |
| **CLIAgent** | `agents/cli_agent.py` | Claude CLI subprocess integration (Pro subscription, no API cost) |
| **GrokAgent** | `agents/grok.py` | xAI API (cheap worker), task classification, quick actions, research |
| **SonnetAgent** | `agents/sonnet.py` | Main conversational agent, reflection, synthesis, newspaper, naming |
| **OpusAgent** | `agents/opus.py` | Deep thinking, weekly synthesis, naming ceremony (manual-only) |
| **Gateway** | `agents/gateway.py` | Central orchestrator: routing, session history, special commands |
| **ToolExecutor** | `agents/tool_executor.py` | Executes spawn_agent/list_subagents tool calls |
| **Nightshift** | `agents/nightshift.py` | Daemon loop: polling, task processing, reflection, newspaper |

### Integration Layer

| Integration | File(s) | Purpose |
|-------------|---------|---------|
| **Telegram** | `integrations/telegram.py` | Bot with /start, /status, /costs, /reflect, message handling, notifications |
| **CLI** | `integrations/cli.py` | Interactive REPL, thinking indicator, session management |

### Service Layer

| Component | File(s) | Purpose |
|-----------|---------|---------|
| **Unified Service** | `service.py` | Single-process: Nightshift thread + FastAPI (REST API + Web UI) |
| **Web UI** | `web/app.py` | HTMX pages: chat, tasks, skills, projects, proposals, reflections, debug, config |
| **Entry Point** | `main.py` | Click CLI: serve, daemon, web, chat, status, costs, reflect, name, etc. |

### Key Design Decisions

1. **Single process, three services** -- Nightshift daemon + REST API + Web UI all in one process
2. **Multi-provider agents** -- Grok (xAI API), Sonnet/Opus (Claude CLI subprocess)
3. **File-based identity** -- soul.md, user.md, reflections as markdown files
4. **SQLite for state** -- Tasks, conversations, costs in one DB
5. **Self-improvement loop** -- Entity proposes code changes, human reviews, git integration
6. **Budget awareness** -- Entity knows its own cost constraints, included in system prompts
7. **Entity-as-system-user** -- Dedicated Linux user, can rename itself, own hostname

---

## 2. What Hearth Does Well

These are the strongest parts of the system and the things that make hearth unique:

### Identity System (Keep, core strength)
- **soul.md / user.md** -- Elegant approach to persistent identity. The entity re-reads its soul at startup. This is the heart of what makes hearth different from a chatbot.
- **Naming ceremony** -- Genuinely novel. The entity earns its name through reflection, then the name propagates to the system user and hostname.
- **Soul edit proposals** -- The entity can propose changes to its own identity, with human review. This is a powerful pattern for controlled self-modification.
- **First awakening** -- The "first boot" concept gives entities a birth moment with continuity.

### Reflection & Memory (Keep, core strength)
- **Daily reflections** as markdown files provide genuine continuity across sessions. The entity can look back at its own evolution.
- **Weekly Opus synthesis** -- Using a stronger model for periodic deep introspection is smart resource allocation.
- **Reflection-informed prompts** -- Recent reflections are injected into system prompts, giving the entity actual memory.

### Self-Improvement Proposals (Keep, core strength)
- The `ProposalManager` is well-designed: create, review, approve/reject, apply, git commit flow.
- Feature branches for proposals (never commit to main) is good safety.
- The entity can analyze its own codebase and propose improvements -- this is the "self-improving agent" value proposition.

### Nightshift Daemon (Keep, needs rearchitecting)
- The concept of an autonomous overnight worker is compelling.
- Morning briefings, autonomous task processing, and scheduled reflection are all strong ideas.
- The "directive" file (`nightshift.md`) letting the human guide autonomous behavior is a good control mechanism.

### Cost Awareness (Keep, good pattern)
- The entity knowing its own budget constraints and including them in system prompts is excellent.
- Budget enforcement with graduated alerts (log -> notify -> restrict -> pause) is well thought out.
- The "self-awareness context" injected into prompts is a great pattern other homestead packages should adopt.

### Multi-Model Architecture (Keep, adapt)
- The tiered model approach (Grok=cheap, Sonnet=mid, Opus=deep) with role-based tool access is solid.
- The CLIAgent pattern (using Claude CLI subprocess to avoid per-token costs with Pro subscription) is clever and practical.

---

## 3. Feature Overlap Analysis

### Herald (Messaging/Comms)

Herald is a dedicated Telegram bot built on aiogram with streaming, session management, message queuing, and markdown-to-HTML conversion. It already has:

| Feature | Hearth Implementation | Herald Implementation | Verdict |
|---------|----------------------|----------------------|---------|
| Telegram bot | `integrations/telegram.py` -- basic python-telegram-bot | `herald/bot.py` -- aiogram, streaming, queue, auth middleware | **Herald wins.** Hearth's is simpler and less robust. |
| Message handling | Gateway routing + agent dispatch | Direct Claude CLI spawning with session management | **Herald wins.** More mature, handles rate limits, cancellation. |
| Message splitting | Basic 4000-char chunks | Smart splitting at newlines/spaces | **Herald wins.** |
| Auth | Single chat_id check | Configurable authorized user list | **Herald wins.** |
| Session management | In-memory dict in Gateway | `SessionManager` with stale detection, rotation | **Herald wins.** |
| Quiet hours | Config-based in `config.py` | Not yet (but should be in herald) | **Hearth has it, move to herald.** |
| Notifications | `send_newspaper()`, `send_alert()` | Not yet (but natural fit) | **Move to herald.** |

**Recommendation:** Delete `integrations/telegram.py` entirely. Herald owns all messaging. Hearth publishes events (reflection complete, task done, morning briefing ready) and herald delivers them.

### Steward (Task Management)

Steward is a dedicated task management system with richer models (blockers, dependencies, human-blocked tasks). It already has:

| Feature | Hearth Implementation | Steward Implementation | Verdict |
|---------|----------------------|------------------------|---------|
| Task CRUD | `core/tasks.py` + `state.py` SQLite | `steward/models.py` + `steward/store.py` (JSON files) | **Steward's model is richer** (blockers, dependencies, assignees, tags). Hearth's is more complete (actually implemented CRUD). |
| Task statuses | pending, in_progress, completed, failed | pending, in_progress, blocked, completed, cancelled | **Steward wins.** `blocked` status is essential for human-in-the-loop. |
| Priority | Integer 1-5 | Enum: low/normal/high/urgent | **Steward wins.** Named priorities are clearer. |
| Blocker tracking | None | `Blocker` dataclass with type (human_input, human_approval, dependency) | **Steward wins.** This is a key differentiator. |
| Source tracking | `source` field (manual, entity, nightshift) | `source` field (herald, almanac, hearth) | **Same pattern, steward designed for monorepo.** |
| Projects | `core/projects.py` -- full implementation | Not yet | **Keep in hearth or move to steward.** See discussion below. |

**Recommendation:** Delete `core/tasks.py` and the tasks table from `state.py`. Hearth uses steward as a dependency for all task operations. The nightshift daemon creates tasks in steward instead of its own DB. Projects are a gray area -- they could live in steward as a "project" concept, or remain in hearth as part of the entity's self-organization. I recommend moving them to steward since projects are not entity-specific.

### Almanac (Scheduling)

Almanac is a dedicated cron/scheduling system with job models, schedule types, and an async scheduler. It has:

| Feature | Hearth Implementation | Almanac Implementation | Verdict |
|---------|----------------------|------------------------|---------|
| Schedule config | `hearth.yaml` schedule section (start/end hours, intervals) | `Job` model with cron, interval, one-shot schedules | **Almanac wins.** Far more flexible. |
| Nightshift/dayshift hours | `config.py` `is_nightshift` property | Can be expressed as almanac jobs | **Almanac is the right home** for this. |
| Reflection scheduling | Hardcoded 4-hour interval in nightshift daemon | `interval` type job | **Almanac should schedule this.** |
| Newspaper scheduling | Hardcoded hour check in nightshift daemon | `cron` type job | **Almanac should schedule this.** |
| Opus synthesis scheduling | Config: day=sunday, hour=2 | `cron` type job | **Almanac should schedule this.** |
| Job actions | N/A (logic embedded in nightshift) | `JobAction`: notify, create_task, run_command, webhook | **Almanac's action system is the right abstraction.** |

**Recommendation:** All scheduling logic moves to almanac. The nightshift daemon stops doing its own time-checking. Instead, almanac fires events/callbacks that hearth's daemon responds to. The `schedule` section of `hearth.yaml` becomes almanac job definitions.

---

## 4. Proposed New Architecture

### Hearth's New Identity

After extracting messaging, tasks, and scheduling, hearth becomes focused on what no other package does:

> **Hearth is the AI entity personality layer.** It owns identity, memory, reflection, self-improvement, and the autonomous daemon that gives the entity agency.

### Package Boundaries

```
homestead/packages/
  herald/     -- Messaging: Telegram, (future: Slack, Discord, Matrix)
  steward/    -- Task management: CRUD, blockers, dependencies, projects
  almanac/    -- Scheduling: cron, intervals, one-shot, job actions
  hearth/     -- AI entity: identity, memory, reflection, self-improvement, daemon
```

### Hearth's New Structure

```
hearth/
  core/
    identity.py        # soul.md, user.md, naming, soul edits (KEEP AS-IS)
    reflections.py     # Daily reflection, weekly synthesis (KEEP, simplify)
    proposals.py       # Self-improvement proposals (KEEP AS-IS)
    skills.py          # Learned skill library (KEEP AS-IS)
    costs.py           # Budget tracking, self-awareness context (KEEP AS-IS)
    config.py          # Config loader (SIMPLIFY: remove schedule/telegram sections)
    state.py           # SQLite KV store + costs (SIMPLIFY: remove tasks/sessions tables)
    nightshift.py      # Nightshift manager (REWRITE: use almanac for scheduling)

  agents/
    base.py            # BaseAgent abstract class (KEEP)
    cli_agent.py       # Claude CLI subprocess integration (KEEP)
    grok.py            # xAI Grok agent (KEEP)
    sonnet.py          # Sonnet conversational agent (KEEP, remove newspaper)
    opus.py            # Opus deep thinking agent (KEEP)
    gateway.py         # Central orchestrator (SIMPLIFY: remove task/telegram commands)
    tool_executor.py   # Tool execution for spawning (KEEP)

  providers/           # MOVE from core/providers/ to top level
    base.py
    claude_cli.py
    xai.py
    openai.py          # (if needed)
    gemini.py          # (if needed)

  daemon.py            # NEW: replaces agents/nightshift.py + service.py
                       # Simple event loop that responds to almanac triggers

  main.py              # CLI entry point (SIMPLIFY)

  # DELETED:
  # - integrations/telegram.py  (herald owns this)
  # - integrations/cli.py       (simplify into main.py or remove)
  # - core/tasks.py             (steward owns this)
  # - core/projects.py          (steward owns this)
  # - core/sessions.py          (simplify or remove)
  # - core/router.py            (already deprecated)
  # - core/tools.py             (rethink for monorepo)
  # - core/api.py               (rethink: hearth API is mostly CRUD for other packages)
  # - web/                      (rethink: should this be a separate package?)
  # - service.py                (replaced by daemon.py)
```

### Dependency Graph

```
                    almanac
                   /       \
                  /         \
    hearth ----steward       herald
       \         |          /
        \        |         /
         \       |        /
          [shared config / events]
```

- **hearth** depends on **steward** (to create/query tasks)
- **hearth** depends on **almanac** (to register scheduled jobs)
- **hearth** publishes events that **herald** consumes (reflection complete, morning briefing, alerts)
- **almanac** fires triggers that **hearth** responds to (time for reflection, time for newspaper, etc.)
- **steward** is the shared task store for all packages

### Inter-Package Communication

The homestead packages need a lightweight event/message bus. Options:

1. **File-based events** (simplest): Write JSON event files to a shared directory. Packages poll or use inotify.
2. **SQLite shared DB**: A shared `homestead.db` with an events table. Packages poll.
3. **Unix domain sockets**: Each package listens on a socket. Direct IPC.
4. **Redis pub/sub**: If Redis is already in the stack.

**Recommendation:** Start with a shared SQLite events table in a homestead-level database. It is simple, requires no additional infrastructure, works with the existing SQLite pattern, and is easy to upgrade later. A `homestead-core` or `homestead-common` package could provide:

```python
# homestead_common/events.py
class EventBus:
    def publish(event_type: str, data: dict, source: str) -> None
    def subscribe(event_type: str, callback: Callable) -> None
    def poll(event_type: str, since: datetime) -> List[Event]
```

### Hearth's New Configuration

```yaml
# hearth.yaml (simplified)

entity:
  home: /home/milo/.hearth
  user: milo

# Agent configuration
agents:
  main: sonnet
  spawnable: [grok, sonnet, opus]

models:
  grok:
    provider: xai
    model: grok-3
    api_key_env: XAI_API_KEY
  sonnet:
    provider: claude-cli
    model: claude-sonnet-4-5-20250929
  opus:
    provider: claude-cli
    model: claude-opus-4-5-20251101

# Budget (hearth-specific, since it owns cost tracking for AI calls)
budgets:
  daily:
    total: 3.00
    grok: 3.00
  alerts:
    - percent: 80
      action: notify  # publishes event -> herald delivers
    - percent: 95
      action: restrict
    - percent: 100
      action: pause

# Nightshift directive (behavioral, not scheduling)
nightshift:
  directive_path: identity/nightshift.md
  max_tasks_per_cycle: 3
  skip_high_complexity: true

# REMOVED: schedule section (almanac owns this)
# REMOVED: telegram section (herald owns this)
# REMOVED: web section (TBD - may move to separate package)

logging:
  level: INFO
  file: logs/hearth.log

security:
  require_confirmation: [rm -rf, git push, sudo]
  forbidden_paths: [/etc, /boot, ~/.ssh/id_*]
```

### Almanac Job Definitions (for hearth-related scheduling)

```yaml
# almanac jobs created by hearth at startup
jobs:
  - name: hearth-reflection
    schedule: {type: interval, expression: "4h"}
    action: {type: publish_event, config: {event: "hearth.reflection.due"}}

  - name: hearth-newspaper
    schedule: {type: cron, expression: "0 6 * * *"}
    action: {type: publish_event, config: {event: "hearth.newspaper.due"}}

  - name: hearth-opus-synthesis
    schedule: {type: cron, expression: "0 2 * * 0"}
    action: {type: publish_event, config: {event: "hearth.synthesis.due"}}

  - name: hearth-nightshift-start
    schedule: {type: cron, expression: "0 22 * * *"}
    action: {type: publish_event, config: {event: "hearth.nightshift.start"}}

  - name: hearth-nightshift-end
    schedule: {type: cron, expression: "0 6 * * *"}
    action: {type: publish_event, config: {event: "hearth.nightshift.end"}}
```

---

## 5. Migration Path

### Phase 1: Extract Tasks to Steward

**Effort:** Medium
**Risk:** Low (steward store is not yet implemented, so we are filling it in)

1. Implement steward's `TaskStore.save()`, `get()`, `list_tasks()`, `delete()` methods.
2. Add a steward client/SDK that hearth imports:
   ```python
   from steward import TaskStore, Task, TaskStatus
   ```
3. Replace all `TaskManager` calls in hearth with steward calls.
4. Migrate `core/projects.py` to steward as a `Project` model (or keep in hearth if projects are deemed entity-specific).
5. Remove the `tasks` table from `state.py` (keep the table for backward compat but stop writing to it).
6. Remove `core/tasks.py`.
7. Update `core/nightshift.py` to create steward tasks instead of hearth tasks.
8. Update `web/app.py` task pages to read from steward.
9. Update `core/api.py` task endpoints to proxy to steward.

### Phase 2: Extract Scheduling to Almanac

**Effort:** Medium
**Risk:** Low

1. Implement almanac's `Scheduler.start()` method.
2. Add an almanac client/SDK:
   ```python
   from almanac import JobStore, Job, Schedule, ScheduleType, JobAction
   ```
3. Create a `hearth/setup_jobs.py` that registers hearth's scheduled jobs with almanac on startup.
4. Rewrite the nightshift daemon to be event-driven:
   - Instead of a `while True` loop with time checks, it subscribes to almanac events.
   - When `hearth.reflection.due` fires, run reflection.
   - When `hearth.newspaper.due` fires, generate newspaper.
   - When `hearth.nightshift.start` fires, enter autonomous mode.
5. Remove the `schedule` section from `hearth.yaml`.
6. Remove `is_nightshift`, `current_interval`, `is_quiet_hours` from `config.py`.

### Phase 3: Extract Messaging to Herald

**Effort:** Low-Medium
**Risk:** Low

1. Delete `integrations/telegram.py` entirely.
2. Herald already handles Telegram messaging. Add an event subscription system so herald can:
   - Receive "send notification" events from hearth.
   - Forward user messages to hearth's gateway for processing.
3. Add a `hearth.notify(channel, message, priority)` method that publishes to the event bus.
4. Herald picks up these events and delivers via Telegram (or future Slack/Discord).
5. Move quiet hours config to herald.
6. The morning newspaper becomes: hearth generates content -> publishes event -> herald delivers via Telegram.

### Phase 4: Simplify Hearth Internals

**Effort:** Medium
**Risk:** Medium (touches many files)

1. **Simplify `state.py`:** Remove tasks, sessions tables. Keep: KV store, costs, conversations.
2. **Simplify `config.py`:** Remove schedule, telegram, web sections.
3. **Simplify `gateway.py`:** Remove special commands for tasks. Keep: conversation routing, identity commands (status, costs, reflect, name).
4. **Rewrite `service.py` -> `daemon.py`:**
   - No more nightshift thread -- the daemon IS the main process.
   - It subscribes to almanac events and processes them.
   - The FastAPI server (if kept) runs alongside.
5. **Simplify `api.py`:** Remove task, project, and subagent endpoints (steward provides these). Keep: health, identity, reflections, proposals, skills, costs.
6. **Simplify `web/app.py`:** Remove task and project pages (steward provides UI or hearth proxies). Keep: chat, status, reflections, proposals, skills, config.
7. **Simplify `main.py`:** Remove task-related CLI commands. Keep: serve, daemon, chat, status, reflect, name, costs, identity.

### Phase 5: Shared Infrastructure

**Effort:** Medium
**Risk:** Low (new code, not breaking existing)

1. Create `homestead-common` package with:
   - `EventBus` for inter-package communication
   - Shared config loading utilities
   - Common logging setup
2. All packages depend on `homestead-common`.
3. Define standard event types:
   ```
   hearth.reflection.complete
   hearth.newspaper.ready
   hearth.alert
   hearth.proposal.created
   steward.task.created
   steward.task.completed
   steward.task.blocked
   almanac.job.fired
   herald.message.received
   ```

---

## 6. What Stays in Hearth

After the migration, hearth's core identity becomes clear:

### The Entity Personality Layer

1. **Identity Management** (`core/identity.py`)
   - soul.md loading and system prompt building
   - user.md (human context)
   - Naming ceremony
   - Soul edit proposals with human review
   - First boot / first awakening
   - Entity name in state DB

2. **Reflection & Memory** (`core/reflections.py`)
   - Daily reflection generation (agent-powered)
   - Weekly Opus synthesis
   - Reflection storage (markdown files)
   - Reflection-informed prompt building

3. **Self-Improvement** (`core/proposals.py`)
   - Code analysis and improvement proposals
   - Diff generation, review workflow
   - Apply and git commit integration
   - Proposal history

4. **Learned Skills** (`core/skills.py`)
   - Skill creation from experience
   - Skill library (markdown files)
   - Skill search and tagging
   - Skill-informed prompt building

5. **Cost Awareness** (`core/costs.py`)
   - API cost tracking per model
   - Budget enforcement with graduated alerts
   - Self-awareness context for prompts
   - Cost reporting

6. **Agent Framework** (`agents/`)
   - BaseAgent / CLIAgent abstractions
   - Multi-provider support (xAI, Claude CLI, etc.)
   - Gateway orchestration
   - Subagent spawning and tool use

7. **Autonomous Daemon** (`daemon.py`)
   - Event-driven operation (responds to almanac triggers)
   - Autonomous task processing (reads from steward)
   - Reflection execution
   - Morning briefing generation
   - Self-improvement analysis
   - Nightshift directive following

### What Hearth Should NOT Own

- Task CRUD and task state (steward)
- Project management (steward)
- Schedule definitions and timer logic (almanac)
- Telegram/Slack message handling (herald)
- Message formatting and delivery (herald)
- Session management for messaging platforms (herald)

---

## 7. Open Questions

1. **Web UI ownership:** Should the web UI stay in hearth, move to a dedicated `homestead-web` package, or should each package expose its own API and a unified frontend consumes them all? Recommendation: Keep hearth's web UI for now but have it consume steward/almanac APIs for task and schedule views. Long-term, a unified homestead dashboard makes more sense.

2. **REST API consolidation:** Currently hearth's API exposes everything (tasks, proposals, skills, etc.). Should each package have its own API, or should there be a unified homestead API gateway? Recommendation: Each package exposes its own API. A future `homestead-gateway` can unify them.

3. **Conversations table:** The conversations table in `state.py` stores chat history. Herald also manages sessions. Who owns conversation persistence? Recommendation: Herald owns message transport and session state. Hearth owns conversation history for prompt building (the entity's memory of what was discussed).

4. **Projects:** Are projects entity-specific (the entity's personal project tracking) or shared infrastructure? Recommendation: Move to steward. Projects are fundamentally task organization, and steward is the task layer. The entity's "personal" relationship to projects is expressed through the soul.md and reflections, not the project data model itself.

5. **CLI integration (`integrations/cli.py`):** This is a direct terminal REPL for chatting with the entity. It does not overlap with any other package. Keep it in hearth but simplify -- it can use the Gateway directly without going through integrations.

6. **Subagent spawning:** The `sessions.py` / `tool_executor.py` / `tools.py` system lets agents spawn subagents. This is hearth-specific (agent orchestration) and should stay, but the `sessions` table in StateDB can be simplified or moved to in-memory only since subagent sessions are ephemeral.

---

## 8. Summary

| Component | Current Home | New Home | Action |
|-----------|-------------|----------|--------|
| Identity (soul, naming, prompts) | hearth | hearth | Keep |
| Reflections & synthesis | hearth | hearth | Keep |
| Self-improvement proposals | hearth | hearth | Keep |
| Learned skills | hearth | hearth | Keep |
| Cost tracking & budgets | hearth | hearth | Keep |
| Agent framework (base, CLI, providers) | hearth | hearth | Keep |
| Gateway / orchestrator | hearth | hearth | Simplify |
| Subagent spawning | hearth | hearth | Keep |
| Nightshift daemon | hearth | hearth | Rewrite (event-driven) |
| Task CRUD | hearth | **steward** | Migrate |
| Project management | hearth | **steward** | Migrate |
| Schedule/timer logic | hearth | **almanac** | Migrate |
| Nightshift/dayshift hours | hearth | **almanac** | Migrate |
| Reflection scheduling | hearth | **almanac** | Migrate |
| Newspaper scheduling | hearth | **almanac** | Migrate |
| Telegram bot | hearth | **herald** | Delete, use herald |
| Telegram notifications | hearth | **herald** | Migrate |
| Quiet hours | hearth | **herald** | Migrate |
| Web UI | hearth | hearth (for now) | Simplify |
| REST API | hearth | hearth (for now) | Simplify |

### The Pitch

After this refactor, hearth becomes the thing no other framework does well: **a persistent AI personality that remembers, reflects, improves itself, and operates autonomously** -- while delegating the infrastructure concerns (messaging, task tracking, scheduling) to purpose-built packages in the homestead monorepo.

Hearth answers: "Who is this entity, what does it remember, and how does it grow?"

Everything else is plumbing -- and homestead has dedicated packages for the plumbing.
