# Manor API Reference

Complete reference for the Manor REST and WebSocket API. The API is served by FastAPI on port 8700 (configurable via `MANOR_PORT`).

**Base URL:** `http://localhost:8700`

---

## Table of Contents

- [Health](#health)
- [Sessions](#sessions)
- [Logs](#logs)
- [Tasks](#tasks)
- [Jobs](#jobs)
- [Skills](#skills)
- [Lore](#lore)
- [Scratchpad](#scratchpad)
- [Config](#config)
- [Chat (WebSocket)](#chat-websocket)

---

## Health

### GET /health

Health check endpoint.

**Response:**

```json
{
    "status": "ok",
    "service": "manor-api"
}
```

---

## Sessions

Session management for Herald conversations. Reads and writes the Herald sessions SQLite database.

### GET /api/sessions

List all sessions across all chats, ordered by most recently active.

**Response:**

```json
[
    {
        "chat_id": 123456789,
        "name": "default",
        "user_id": 123456789,
        "claude_session_id": "a1b2c3d4-...",
        "model": "claude",
        "is_active": true,
        "created_at": 1700000000.0,
        "last_active_at": 1700001000.0,
        "message_count": 15
    }
]
```

### GET /api/sessions/{chat_id}

List sessions for a specific Telegram chat.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `chat_id` | integer | Telegram chat ID |

**Response:** Same array format as above, filtered to the given chat.

### POST /api/sessions

Create a new session and set it as active for the chat. Deactivates all other sessions for that chat.

**Request Body:**

```json
{
    "chat_id": 123456789,
    "name": "research",
    "model": "grok",
    "user_id": 123456789
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `chat_id` | integer | (required) | Telegram chat ID |
| `name` | string | `"default"` | Session name |
| `model` | string | `"claude"` | Model: claude, sonnet, opus, grok |
| `user_id` | integer | `0` | Telegram user ID |

**Response (201):**

```json
{
    "chat_id": 123456789,
    "name": "research",
    "user_id": 123456789,
    "claude_session_id": "e5f6g7h8-...",
    "model": "grok",
    "is_active": true,
    "created_at": 1700002000.0,
    "last_active_at": 1700002000.0,
    "message_count": 0
}
```

**Errors:**

| Status | Condition |
|---|---|
| 409 | Session with that name already exists for the chat |

### PUT /api/sessions/{chat_id}/{name}/activate

Switch the active session for a chat to the named session.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `chat_id` | integer | Telegram chat ID |
| `name` | string | Session name to activate |

**Response:** The activated session object.

**Errors:**

| Status | Condition |
|---|---|
| 404 | Session not found |

### PUT /api/sessions/{chat_id}/{name}/model

Change the model for an existing session.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `chat_id` | integer | Telegram chat ID |
| `name` | string | Session name |

**Request Body:**

```json
{
    "model": "sonnet"
}
```

**Response:** The updated session object.

**Errors:**

| Status | Condition |
|---|---|
| 404 | Session not found |

### DELETE /api/sessions/{chat_id}/{name}

Delete a session permanently.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `chat_id` | integer | Telegram chat ID |
| `name` | string | Session name |

**Response:**

```json
{
    "deleted": true,
    "chat_id": 123456789,
    "name": "research"
}
```

**Errors:**

| Status | Condition |
|---|---|
| 404 | Session not found |

---

## Logs

Query the Watchtower structured log database.

### GET /api/logs

Query logs with flexible filtering. Returns most recent logs first.

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `hours` | float | `24` | How many hours back to search |
| `level` | string | (none) | Filter by log level: DEBUG, INFO, WARNING, ERROR |
| `source` | string | (none) | Filter by source prefix (e.g. `herald` matches `herald.bot`) |
| `search` | string | (none) | Substring search within message text |
| `limit` | integer | `100` | Max rows to return (1-1000) |

**Response:**

```json
[
    {
        "id": 42,
        "timestamp": 1700000000.0,
        "level": "INFO",
        "source": "herald.bot",
        "message": "chat=123456789 claude responded (1523 chars)",
        "data": null,
        "session_id": null,
        "chat_id": 123456789
    }
]
```

Returns an empty array if the watchtower database or `logs` table does not yet exist.

### GET /api/logs/summary

Summary of log counts grouped by source and level.

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `hours` | float | `24` | How many hours back |

**Response:**

```json
{
    "herald": {
        "INFO": 142,
        "WARNING": 3,
        "ERROR": 1
    },
    "almanac": {
        "INFO": 28
    }
}
```

Returns an empty object if no logs exist.

---

## Tasks

Task management (Steward). Create, update, and track tasks with priorities, blockers, and dependencies.

### GET /api/tasks/summary

Return task counts grouped by status.

**Response:**

```json
{
    "pending": 5,
    "in_progress": 2,
    "blocked": 1,
    "completed": 12,
    "cancelled": 0,
    "total": 20
}
```

### GET /api/tasks

List tasks with optional filtering.

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `status` | string | (none) | Filter by status: pending, in_progress, blocked, completed, cancelled |
| `assignee` | string | (none) | Filter by assignee: auto, user, or agent name |
| `tag` | string | (none) | Filter by tag (substring match in JSON) |

**Response:**

```json
[
    {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "title": "Implement webhook notifications",
        "description": "Add webhook support to the almanac scheduler",
        "status": "in_progress",
        "priority": "high",
        "assignee": "auto",
        "blockers": [],
        "depends_on": [],
        "created_at": 1700000000.0,
        "updated_at": 1700001000.0,
        "completed_at": null,
        "tags": ["almanac", "feature"],
        "notes": ["Started implementation 2024-01-15"],
        "source": "herald"
    }
]
```

**Errors:**

| Status | Condition |
|---|---|
| 400 | Invalid status value |

### GET /api/tasks/{task_id}

Get a single task by ID.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `task_id` | string | Task UUID |

**Response:** Single task object (same structure as list items).

**Errors:**

| Status | Condition |
|---|---|
| 404 | Task not found |

### POST /api/tasks

Create a new task.

**Request Body:**

```json
{
    "title": "Add dark mode to Manor",
    "description": "Implement a theme toggle in the settings panel",
    "status": "pending",
    "priority": "normal",
    "assignee": "auto",
    "depends_on": [],
    "tags": ["manor", "ui"],
    "notes": [],
    "source": "manor"
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `title` | string | (required) | Task title |
| `description` | string | `""` | Detailed description |
| `status` | string | `"pending"` | Initial status |
| `priority` | string | `"normal"` | low, normal, high, urgent |
| `assignee` | string | `"auto"` | Who owns the task |
| `depends_on` | string[] | `[]` | Task IDs this depends on |
| `tags` | string[] | `[]` | Tags for categorization |
| `notes` | string[] | `[]` | Initial notes |
| `source` | string | `""` | Which module created it |

**Response (201):** The created task object.

**Errors:**

| Status | Condition |
|---|---|
| 400 | Invalid status or priority value |

### PUT /api/tasks/{task_id}

Partial update of an existing task. Only provided fields are changed.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `task_id` | string | Task UUID |

**Request Body:**

```json
{
    "status": "in_progress",
    "priority": "high",
    "tags": ["manor", "ui", "in-progress"]
}
```

All fields are optional. Only include the fields you want to change. The `updated_at` timestamp is set automatically. Setting `status` to `"completed"` also sets `completed_at`.

**Response:** The updated task object.

**Errors:**

| Status | Condition |
|---|---|
| 400 | Invalid status or priority value |
| 404 | Task not found |

### PUT /api/tasks/{task_id}/status

Quick status change for a task.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `task_id` | string | Task UUID |

**Request Body:**

```json
{
    "status": "completed"
}
```

**Response:** The updated task object.

**Errors:**

| Status | Condition |
|---|---|
| 400 | Invalid status value |
| 404 | Task not found |

### POST /api/tasks/{task_id}/notes

Append a note to a task.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `task_id` | string | Task UUID |

**Request Body:**

```json
{
    "note": "Reviewed the implementation, needs test coverage"
}
```

**Response:** The updated task object (with the new note appended).

**Errors:**

| Status | Condition |
|---|---|
| 404 | Task not found |

### POST /api/tasks/{task_id}/blockers

Add a blocker to a task.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `task_id` | string | Task UUID |

**Request Body:**

```json
{
    "type": "human_input",
    "description": "Need database schema design decision"
}
```

| Field | Type | Description |
|---|---|---|
| `type` | string | human_input, human_approval, human_action, dependency |
| `description` | string | What is blocking the task |

**Response:** The updated task object (with the new blocker appended).

**Errors:**

| Status | Condition |
|---|---|
| 400 | Invalid blocker type |
| 404 | Task not found |

### PUT /api/tasks/{task_id}/blockers/{index}/resolve

Resolve a specific blocker by its index in the blockers array.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `task_id` | string | Task UUID |
| `index` | integer | Zero-based blocker index |

**Request Body:**

```json
{
    "resolved_by": "user",
    "resolution": "Use a single tasks table with JSON columns for flexibility"
}
```

**Response:** The updated task object.

**Errors:**

| Status | Condition |
|---|---|
| 404 | Task not found or blocker index out of range |

### DELETE /api/tasks/{task_id}

Delete a task permanently.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `task_id` | string | Task UUID |

**Response:**

```json
{
    "deleted": true,
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Errors:**

| Status | Condition |
|---|---|
| 404 | Task not found |

---

## Jobs

Job scheduling (Almanac). Create, update, enable/disable, and manually trigger scheduled jobs.

### GET /api/jobs/summary

Count of jobs by schedule type and enabled/disabled status.

**Response:**

```json
{
    "by_schedule_type": {
        "cron": 3,
        "interval": 1,
        "once": 2
    },
    "enabled": 4,
    "disabled": 2,
    "total": 6
}
```

### GET /api/jobs

List all scheduled jobs.

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `enabled_only` | boolean | `false` | Only return enabled jobs |

**Response:**

```json
[
    {
        "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "name": "Morning briefing",
        "description": "Send a daily summary at 9 AM",
        "schedule_type": "cron",
        "schedule_value": "0 9 * * *",
        "action_type": "outbox",
        "action_config": {
            "chat_id": 123456789,
            "agent_name": "almanac",
            "message": "Good morning. Here is your daily briefing."
        },
        "enabled": true,
        "last_run_at": 1700000000.0,
        "next_run_at": 1700086400.0,
        "run_count": 14,
        "created_at": 1699000000.0,
        "tags": ["daily", "notification"],
        "source": "manor"
    }
]
```

### GET /api/jobs/{job_id}

Get a single job by ID.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `job_id` | string | Job UUID |

**Response:** Single job object.

**Errors:**

| Status | Condition |
|---|---|
| 404 | Job not found |

### POST /api/jobs

Create a new scheduled job. The `next_run_at` timestamp is computed automatically from the schedule.

**Request Body:**

```json
{
    "name": "Weekly backup reminder",
    "description": "Remind to run backups every Sunday at midnight",
    "schedule_type": "cron",
    "schedule_value": "0 0 * * 6",
    "action_type": "outbox",
    "action_config": {
        "chat_id": 123456789,
        "agent_name": "almanac",
        "message": "Reminder: run weekly backups."
    },
    "enabled": true,
    "tags": ["maintenance"],
    "source": "manor"
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | string | (required) | Job name |
| `description` | string | `""` | Description |
| `schedule_type` | string | (required) | `cron`, `interval`, or `once` |
| `schedule_value` | string | (required) | Cron expression, seconds (interval), or ISO datetime (once) |
| `action_type` | string | (required) | `outbox`, `command`, or `webhook` |
| `action_config` | object | `{}` | Action-specific configuration (see below) |
| `enabled` | boolean | `true` | Whether the job is active |
| `tags` | string[] | `[]` | Tags for categorization |
| `source` | string | `"manor"` | Which module created the job |

**Schedule Types:**

| Type | `schedule_value` format | Example |
|---|---|---|
| `cron` | Standard 5-field cron expression | `"0 9 * * 1-5"` (weekdays at 9 AM) |
| `interval` | Seconds between runs | `"3600"` (every hour) |
| `once` | ISO 8601 datetime | `"2024-12-31T23:59:00"` |

**Action Types:**

| Type | Config fields |
|---|---|
| `outbox` | `chat_id` (int), `agent_name` (str), `message` (str) |
| `command` | `command` (str), `args` (str[]), `timeout` (int, default 60) |
| `webhook` | `url` (str), `method` (str, default POST), `headers` (obj), `body` (str) |

**Response (201):** The created job object with computed `next_run_at`.

**Errors:**

| Status | Condition |
|---|---|
| 400 | Invalid schedule expression |

### PUT /api/jobs/{job_id}

Partial update of an existing job. Only provided fields are changed. If the schedule is modified, `next_run_at` is recomputed.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `job_id` | string | Job UUID |

**Request Body:**

```json
{
    "schedule_value": "0 10 * * *",
    "description": "Changed to 10 AM"
}
```

All fields are optional.

**Response:** The updated job object.

**Errors:**

| Status | Condition |
|---|---|
| 400 | Invalid schedule expression |
| 404 | Job not found |

### PUT /api/jobs/{job_id}/toggle

Enable or disable a job. When re-enabling, `next_run_at` is recomputed from the current time.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `job_id` | string | Job UUID |

**Request Body:**

```json
{
    "enabled": false
}
```

**Response:** The updated job object.

**Errors:**

| Status | Condition |
|---|---|
| 404 | Job not found |

### POST /api/jobs/{job_id}/run

Manually trigger a job, executing its action immediately. Also marks the run (increments `run_count`, updates `last_run_at`, recomputes `next_run_at`).

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `job_id` | string | Job UUID |

**Response (success):**

```json
{
    "executed": true,
    "job": { ... }
}
```

**Response (almanac not available):**

```json
{
    "executed": false,
    "id": "b2c3d4e5-...",
    "note": "almanac package not available, marked run only"
}
```

**Errors:**

| Status | Condition |
|---|---|
| 404 | Job not found |
| 500 | Job execution failed |

### DELETE /api/jobs/{job_id}

Delete a job permanently.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `job_id` | string | Job UUID |

**Response:**

```json
{
    "deleted": true,
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901"
}
```

**Errors:**

| Status | Condition |
|---|---|
| 404 | Job not found |

---

## Skills

Manage skill files (markdown with YAML front-matter) stored at `~/.homestead/skills/`.

### GET /api/skills

List all skills. Returns summaries without full content.

**Response:**

```json
[
    {
        "name": "git-workflow",
        "description": "Standard git commit and PR workflow",
        "tags": ["git", "workflow"],
        "filename": "git-workflow.md"
    }
]
```

### GET /api/skills/{name}

Get the full content of a skill by name. Tries exact filename match first (`{name}.md`), then searches by the `name` field in front-matter.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `name` | string | Skill name (matches filename stem or front-matter name) |

**Response:**

```json
{
    "name": "git-workflow",
    "description": "Standard git commit and PR workflow",
    "content": "When committing changes:\n1. Use conventional commit messages\n...",
    "tags": ["git", "workflow"],
    "filename": "git-workflow.md"
}
```

**Errors:**

| Status | Condition |
|---|---|
| 404 | Skill not found |

### PUT /api/skills/{name}

Create or update a skill file. The filename is derived from the name: lowercased, spaces replaced with hyphens, `.md` extension.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `name` | string | Skill name |

**Request Body:**

```json
{
    "description": "Standard git commit and PR workflow",
    "content": "When committing changes:\n1. Use conventional commit messages\n2. Keep commits atomic\n3. Always run tests before pushing",
    "tags": ["git", "workflow"]
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `description` | string | `""` | Short description |
| `content` | string | (required) | Skill body (markdown) |
| `tags` | string[] | `[]` | Tags for categorization and search |

**Response:**

```json
{
    "name": "git-workflow",
    "description": "Standard git commit and PR workflow",
    "content": "When committing changes:\n1. ...",
    "tags": ["git", "workflow"],
    "filename": "git-workflow.md"
}
```

### DELETE /api/skills/{name}

Delete a skill file.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `name` | string | Skill name |

**Response:**

```json
{
    "deleted": true,
    "name": "git-workflow"
}
```

**Errors:**

| Status | Condition |
|---|---|
| 404 | Skill not found |

---

## Lore

Read and write AI identity files from the `lore/` directory.

### GET /api/lore

List all lore files with metadata.

**Response:**

```json
[
    {
        "filename": "soul.md",
        "size": 2048,
        "modified": 1700000000.0
    },
    {
        "filename": "claude.md",
        "size": 3512,
        "modified": 1700000000.0
    }
]
```

### GET /api/lore/{filename}

Read the content of a lore file.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `filename` | string | Lore filename (e.g. `soul.md`) |

**Response:**

```json
{
    "filename": "soul.md",
    "content": "# Soul\n\nI am a personal AI assistant...",
    "size": 2048,
    "modified": 1700000000.0
}
```

**Errors:**

| Status | Condition |
|---|---|
| 400 | Invalid filename (directory traversal attempt) |
| 404 | File not found |

### PUT /api/lore/{filename}

Create or update a lore file.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `filename` | string | Lore filename (e.g. `soul.md`) |

**Request Body:**

```json
{
    "content": "# Soul\n\nUpdated identity content..."
}
```

**Response:**

```json
{
    "filename": "soul.md",
    "content": "# Soul\n\nUpdated identity content...",
    "size": 1234,
    "modified": 1700002000.0
}
```

**Errors:**

| Status | Condition |
|---|---|
| 400 | Invalid filename (directory traversal attempt) |

---

## Scratchpad

Read, write, and delete persistent AI memory files from `~/.homestead/scratchpad/`.

### GET /api/scratchpad

List all scratchpad files with metadata.

**Response:**

```json
[
    {
        "filename": "project-notes.md",
        "size": 512,
        "modified": 1700000000.0
    }
]
```

### GET /api/scratchpad/{filename}

Read the content of a scratchpad file.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `filename` | string | Scratchpad filename (e.g. `project-notes.md`) |

**Response:**

```json
{
    "filename": "project-notes.md",
    "content": "# Project Notes\n\nCurrent priorities:\n- ...",
    "size": 512,
    "modified": 1700000000.0
}
```

**Errors:**

| Status | Condition |
|---|---|
| 400 | Invalid filename (directory traversal attempt) |
| 404 | File not found |

### PUT /api/scratchpad/{filename}

Create or update a scratchpad file.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `filename` | string | Scratchpad filename |

**Request Body:**

```json
{
    "content": "# Project Notes\n\nUpdated priorities:\n- ..."
}
```

**Response:**

```json
{
    "filename": "project-notes.md",
    "content": "# Project Notes\n\nUpdated priorities:\n- ...",
    "size": 256,
    "modified": 1700002000.0
}
```

**Errors:**

| Status | Condition |
|---|---|
| 400 | Invalid filename (directory traversal attempt) |

### DELETE /api/scratchpad/{filename}

Delete a scratchpad file.

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `filename` | string | Scratchpad filename |

**Response:**

```json
{
    "deleted": true,
    "filename": "project-notes.md"
}
```

**Errors:**

| Status | Condition |
|---|---|
| 400 | Invalid filename (directory traversal attempt) |
| 404 | File not found |

---

## Config

System configuration and agent identity endpoints.

### GET /api/config

Return current configuration with secrets redacted.

**Response:**

```json
{
    "homestead_data_dir": "~/.homestead",
    "herald_data_dir": "/home/user/homestead/packages/herald/data",
    "lore_dir": "/home/user/homestead/lore",
    "claude_cli_path": "claude",
    "allowed_origins": ["http://localhost:3000"],
    "claude_timeout_s": 300.0,
    "max_turns": 10,
    "port": 8700,
    "watchtower_db": "/home/user/.homestead/watchtower.db",
    "outbox_db": "/home/user/.homestead/outbox.db",
    "sessions_db": "/home/user/homestead/packages/herald/data/sessions.db",
    "skills_dir": "/home/user/.homestead/skills",
    "scratchpad_dir": "/home/user/.homestead/scratchpad"
}
```

### GET /api/agents

List all registered agent identities.

**Response:**

```json
[
    {
        "name": "herald",
        "display_name": "Herald",
        "emoji": "\ud83d\udcef",
        "model_tier": "claude-cli"
    },
    {
        "name": "nightshift",
        "display_name": "Nightshift",
        "emoji": "\ud83c\udf19",
        "model_tier": "sonnet"
    },
    {
        "name": "researcher",
        "display_name": "Research",
        "emoji": "\ud83d\udd0d",
        "model_tier": "grok"
    },
    {
        "name": "steward",
        "display_name": "Steward",
        "emoji": "\ud83d\udccb",
        "model_tier": "sonnet"
    },
    {
        "name": "hearth",
        "display_name": "Hearth",
        "emoji": "\ud83c\udfe0",
        "model_tier": "sonnet"
    }
]
```

---

## Chat (WebSocket)

Real-time chat with Claude via WebSocket. Spawns a Claude CLI process and streams the response.

### WS /ws/chat

**Connection URL:** `ws://localhost:8700/ws/chat`

The WebSocket endpoint accepts JSON messages and streams back JSON responses. The connection stays open for multiple messages.

#### Client -> Server

Send a JSON message to start a conversation turn:

```json
{
    "session_name": "default",
    "chat_id": 0,
    "message": "What is the capital of France?"
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `session_name` | string | `"default"` | Session name (created automatically if it does not exist) |
| `chat_id` | integer | `0` | Chat ID (use 0 for web-only sessions) |
| `message` | string | (required) | The user's message |

#### Server -> Client

The server sends three types of JSON messages:

**Delta (streaming text):**

Sent incrementally as Claude generates text. Concatenate all `delta` texts to build the full response progressively.

```json
{
    "type": "delta",
    "text": "The capital of "
}
```

**Result (final response):**

Sent once when Claude finishes. Contains the complete response text and the session ID (which may have changed on the first message of a new session).

```json
{
    "type": "result",
    "text": "The capital of France is Paris.",
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Error:**

Sent when something goes wrong (invalid JSON, empty message, Claude process error, etc.).

```json
{
    "type": "error",
    "message": "claude exited with code 1: session not found"
}
```

#### Session Behavior

- If the session does not exist, it is created automatically with `model: "claude"` and `user_id: 0`.
- If `message_count > 0`, the Claude CLI is invoked with `--resume <session_id>` to continue the existing conversation.
- After each response, `message_count` and `last_active_at` are updated.
- If Claude returns a new `session_id` (happens on the first message), the stored session is updated.

#### Example WebSocket Flow

```
Client                                          Server
  |                                               |
  |  connect ws://localhost:8700/ws/chat          |
  | --------------------------------------------> |
  |                                               |  accept()
  |  {"session_name":"default","chat_id":0,       |
  |   "message":"Hello"}                          |
  | --------------------------------------------> |
  |                                               |  spawn claude CLI
  |                    {"type":"delta","text":"Hi"}|
  | <-------------------------------------------- |
  |          {"type":"delta","text":" there!"}     |
  | <-------------------------------------------- |
  |  {"type":"result","text":"Hi there!",         |
  |   "session_id":"abc-123"}                     |
  | <-------------------------------------------- |
  |                                               |
  |  {"session_name":"default","chat_id":0,       |
  |   "message":"What was I saying?"}             |
  | --------------------------------------------> |
  |                                               |  spawn claude --resume abc-123
  |                    {"type":"delta","text":"You"|
  | <-------------------------------------------- |
  |        {"type":"delta","text":" said hello."}  |
  | <-------------------------------------------- |
  |  {"type":"result","text":"You said hello.",   |
  |   "session_id":"abc-123"}                     |
  | <-------------------------------------------- |
  |                                               |
  |  close                                        |
  | --------------------------------------------> |
```
