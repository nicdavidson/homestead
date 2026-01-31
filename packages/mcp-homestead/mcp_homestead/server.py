"""
MCP (Model Context Protocol) server for Homestead.

Stdio-based JSON-RPC server that exposes the Manor API as tools for Claude CLI.
All logging goes to stderr; stdout is reserved for the MCP JSON-RPC channel.
"""

from __future__ import annotations

import json
import os
import sys
import traceback

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MANOR_API = os.environ.get("MANOR_API_URL", "http://localhost:8700")
SERVER_NAME = "mcp-homestead"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2024-11-05"

# ---------------------------------------------------------------------------
# HTTP client (lazy-initialized)
# ---------------------------------------------------------------------------

_client: httpx.Client | None = None


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(base_url=MANOR_API, timeout=30.0)
    return _client


# ---------------------------------------------------------------------------
# Logging helper — everything to stderr
# ---------------------------------------------------------------------------


def log(msg: str) -> None:
    print(f"[{SERVER_NAME}] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[dict] = [
    # ── Tasks ──────────────────────────────────────────────────────────
    {
        "name": "list_tasks",
        "description": "List tasks with optional filtering by status, assignee, or tag.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by task status (e.g. open, in_progress, done).",
                },
                "assignee": {
                    "type": "string",
                    "description": "Filter by assignee name.",
                },
                "tag": {
                    "type": "string",
                    "description": "Filter by tag.",
                },
            },
        },
    },
    {
        "name": "get_task",
        "description": "Get a single task by its ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task ID.",
                },
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "create_task",
        "description": "Create a new task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Task title.",
                },
                "description": {
                    "type": "string",
                    "description": "Task description.",
                },
                "priority": {
                    "type": "string",
                    "description": "Priority level (e.g. low, medium, high, critical).",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tags.",
                },
                "assignee": {
                    "type": "string",
                    "description": "Assignee name.",
                },
            },
            "required": ["title"],
        },
    },
    {
        "name": "update_task",
        "description": "Update fields on an existing task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task ID to update.",
                },
                "title": {"type": "string", "description": "New title."},
                "description": {"type": "string", "description": "New description."},
                "priority": {"type": "string", "description": "New priority."},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New tags list.",
                },
                "assignee": {"type": "string", "description": "New assignee."},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "update_task_status",
        "description": "Change the status of a task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The task ID."},
                "status": {
                    "type": "string",
                    "description": "New status (e.g. open, in_progress, done).",
                },
            },
            "required": ["task_id", "status"],
        },
    },
    {
        "name": "add_task_note",
        "description": "Add a note/comment to a task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The task ID."},
                "note": {"type": "string", "description": "The note content."},
            },
            "required": ["task_id", "note"],
        },
    },
    {
        "name": "delete_task",
        "description": "Delete a task by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The task ID to delete."},
            },
            "required": ["task_id"],
        },
    },
    # ── Jobs ───────────────────────────────────────────────────────────
    {
        "name": "list_jobs",
        "description": "List all scheduled jobs.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "create_job",
        "description": "Create a new scheduled job.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Job name."},
                "description": {"type": "string", "description": "Job description."},
                "schedule_type": {
                    "type": "string",
                    "description": "Schedule type (e.g. cron, interval).",
                },
                "schedule_value": {
                    "type": "string",
                    "description": "Schedule value (cron expression or interval spec).",
                },
                "action_type": {
                    "type": "string",
                    "description": "Action type to run.",
                },
                "action_config": {
                    "type": "object",
                    "description": "Configuration object for the action.",
                },
            },
            "required": ["name", "schedule_type", "schedule_value", "action_type"],
        },
    },
    {
        "name": "update_job",
        "description": "Update an existing job.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "The job ID to update."},
                "name": {"type": "string", "description": "New name."},
                "description": {"type": "string", "description": "New description."},
                "schedule_type": {"type": "string", "description": "New schedule type."},
                "schedule_value": {"type": "string", "description": "New schedule value."},
                "action_type": {"type": "string", "description": "New action type."},
                "action_config": {"type": "object", "description": "New action config."},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "toggle_job",
        "description": "Enable or disable a scheduled job.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "The job ID."},
                "enabled": {
                    "type": "boolean",
                    "description": "True to enable, false to disable.",
                },
            },
            "required": ["job_id", "enabled"],
        },
    },
    {
        "name": "trigger_job",
        "description": "Manually trigger a scheduled job to run immediately.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "The job ID to trigger."},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "delete_job",
        "description": "Delete a scheduled job.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "The job ID to delete."},
            },
            "required": ["job_id"],
        },
    },
    # ── Lore ───────────────────────────────────────────────────────────
    {
        "name": "list_lore",
        "description": "List all lore files (persistent knowledge base).",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "read_lore",
        "description": "Read the contents of a lore file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Name of the lore file to read.",
                },
            },
            "required": ["filename"],
        },
    },
    {
        "name": "write_lore",
        "description": "Create or update a lore file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Name of the lore file.",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write.",
                },
            },
            "required": ["filename", "content"],
        },
    },
    # ── Scratchpad ─────────────────────────────────────────────────────
    {
        "name": "list_scratchpad",
        "description": "List all scratchpad files (temporary working notes).",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "read_scratchpad",
        "description": "Read a scratchpad file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Name of the scratchpad file to read.",
                },
            },
            "required": ["filename"],
        },
    },
    {
        "name": "write_scratchpad",
        "description": "Create or update a scratchpad file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Name of the scratchpad file.",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write.",
                },
            },
            "required": ["filename", "content"],
        },
    },
    # ── Proposals ──────────────────────────────────────────────────────
    {
        "name": "propose_code_change",
        "description": "Create a code change proposal for review.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Proposal title."},
                "description": {
                    "type": "string",
                    "description": "Description of the proposed change.",
                },
                "file_path": {
                    "type": "string",
                    "description": "Path of the file to change.",
                },
                "original_content": {
                    "type": "string",
                    "description": "Original file content (or relevant section).",
                },
                "new_content": {
                    "type": "string",
                    "description": "Proposed new content.",
                },
            },
            "required": ["title", "description", "file_path", "original_content", "new_content"],
        },
    },
    {
        "name": "list_proposals",
        "description": "List code change proposals with optional status filter.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by proposal status (e.g. pending, approved, rejected).",
                },
            },
        },
    },
    # ── Usage ──────────────────────────────────────────────────────────
    {
        "name": "get_usage_summary",
        "description": "Get a summary of API/resource usage, optionally since a given timestamp.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "since": {
                    "type": "string",
                    "description": "ISO-8601 timestamp to start from (e.g. 2025-01-01T00:00:00Z).",
                },
            },
        },
    },
    # ── Outbox ─────────────────────────────────────────────────────────
    {
        "name": "send_message",
        "description": "Send a message via the outbox (e.g. to a chat service).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chat_id": {
                    "type": "string",
                    "description": "Target chat/channel ID.",
                },
                "message": {
                    "type": "string",
                    "description": "Message text to send.",
                },
            },
            "required": ["chat_id", "message"],
        },
    },
    # ── Health ─────────────────────────────────────────────────────────
    {
        "name": "check_health",
        "description": "Check the health status of the Homestead system.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


# ---------------------------------------------------------------------------
# Tool handlers — each returns a JSON-serialisable result
# ---------------------------------------------------------------------------


def _api(method: str, path: str, **kwargs) -> dict | list | str:
    """Make an HTTP request to the Manor API and return the parsed response."""
    client = _get_client()
    resp = client.request(method, path, **kwargs)
    resp.raise_for_status()
    if resp.headers.get("content-type", "").startswith("application/json"):
        return resp.json()
    return resp.text


def handle_tool_call(name: str, arguments: dict) -> str:
    """Dispatch a tool call to the appropriate Manor API endpoint.

    Returns a JSON string suitable for the MCP text content response.
    """

    # ── Tasks ──────────────────────────────────────────────────────────
    if name == "list_tasks":
        params = {}
        if arguments.get("status"):
            params["status"] = arguments["status"]
        if arguments.get("assignee"):
            params["assignee"] = arguments["assignee"]
        if arguments.get("tag"):
            params["tag"] = arguments["tag"]
        result = _api("GET", "/api/tasks", params=params)

    elif name == "get_task":
        result = _api("GET", f"/api/tasks/{arguments['task_id']}")

    elif name == "create_task":
        body: dict = {"title": arguments["title"]}
        for key in ("description", "priority", "tags", "assignee"):
            if arguments.get(key) is not None:
                body[key] = arguments[key]
        result = _api("POST", "/api/tasks", json=body)

    elif name == "update_task":
        task_id = arguments.pop("task_id")
        result = _api("PUT", f"/api/tasks/{task_id}", json=arguments)

    elif name == "update_task_status":
        result = _api(
            "PUT",
            f"/api/tasks/{arguments['task_id']}/status",
            json={"status": arguments["status"]},
        )

    elif name == "add_task_note":
        result = _api(
            "POST",
            f"/api/tasks/{arguments['task_id']}/notes",
            json={"note": arguments["note"]},
        )

    elif name == "delete_task":
        result = _api("DELETE", f"/api/tasks/{arguments['task_id']}")

    # ── Jobs ───────────────────────────────────────────────────────────
    elif name == "list_jobs":
        result = _api("GET", "/api/jobs")

    elif name == "create_job":
        body = {
            "name": arguments["name"],
            "schedule_type": arguments["schedule_type"],
            "schedule_value": arguments["schedule_value"],
            "action_type": arguments["action_type"],
        }
        for key in ("description", "action_config"):
            if arguments.get(key) is not None:
                body[key] = arguments[key]
        result = _api("POST", "/api/jobs", json=body)

    elif name == "update_job":
        job_id = arguments.pop("job_id")
        result = _api("PUT", f"/api/jobs/{job_id}", json=arguments)

    elif name == "toggle_job":
        result = _api(
            "PUT",
            f"/api/jobs/{arguments['job_id']}/toggle",
        )

    elif name == "trigger_job":
        result = _api("POST", f"/api/jobs/{arguments['job_id']}/run")

    elif name == "delete_job":
        result = _api("DELETE", f"/api/jobs/{arguments['job_id']}")

    # ── Lore ───────────────────────────────────────────────────────────
    elif name == "list_lore":
        result = _api("GET", "/api/lore")

    elif name == "read_lore":
        result = _api("GET", f"/api/lore/{arguments['filename']}")

    elif name == "write_lore":
        result = _api(
            "PUT",
            f"/api/lore/{arguments['filename']}",
            json={"content": arguments["content"]},
        )

    # ── Scratchpad ─────────────────────────────────────────────────────
    elif name == "list_scratchpad":
        result = _api("GET", "/api/scratchpad")

    elif name == "read_scratchpad":
        result = _api("GET", f"/api/scratchpad/{arguments['filename']}")

    elif name == "write_scratchpad":
        result = _api(
            "PUT",
            f"/api/scratchpad/{arguments['filename']}",
            json={"content": arguments["content"]},
        )

    # ── Proposals ──────────────────────────────────────────────────────
    elif name == "propose_code_change":
        result = _api(
            "POST",
            "/api/proposals",
            json={
                "title": arguments["title"],
                "description": arguments["description"],
                "file_path": arguments["file_path"],
                "original_content": arguments["original_content"],
                "new_content": arguments["new_content"],
            },
        )

    elif name == "list_proposals":
        params = {}
        if arguments.get("status"):
            params["status"] = arguments["status"]
        result = _api("GET", "/api/proposals", params=params)

    # ── Usage ──────────────────────────────────────────────────────────
    elif name == "get_usage_summary":
        params = {}
        if arguments.get("since"):
            params["since"] = arguments["since"]
        result = _api("GET", "/api/usage", params=params)

    # ── Outbox ─────────────────────────────────────────────────────────
    elif name == "send_message":
        result = _api(
            "POST",
            "/api/outbox",
            json={
                "chat_id": arguments["chat_id"],
                "agent_name": arguments.get("agent_name", "milo"),
                "message": arguments["message"],
            },
        )

    # ── Health ─────────────────────────────────────────────────────────
    elif name == "check_health":
        result = _api("GET", "/health/detailed")

    else:
        raise ValueError(f"Unknown tool: {name}")

    # Normalise result to a JSON string for the MCP content response.
    if isinstance(result, str):
        return result
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# JSON-RPC helpers
# ---------------------------------------------------------------------------


def _jsonrpc_response(id: int | str | None, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": id, "result": result}


def _jsonrpc_error(id: int | str | None, code: int, message: str, data: str | None = None) -> dict:
    err: dict = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": id, "error": err}


# ---------------------------------------------------------------------------
# Request handling
# ---------------------------------------------------------------------------


def handle_request(request: dict) -> dict | None:
    """Process a single JSON-RPC request and return the response (or None for notifications)."""
    req_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params", {})

    # -- initialize --------------------------------------------------------
    if method == "initialize":
        return _jsonrpc_response(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {
                "tools": {},
            },
            "serverInfo": {
                "name": SERVER_NAME,
                "version": SERVER_VERSION,
            },
        })

    # -- notifications (no response required) ------------------------------
    if method == "notifications/initialized":
        log("Client initialized.")
        return None

    if method == "notifications/cancelled":
        log(f"Request cancelled: {params}")
        return None

    # -- tools/list --------------------------------------------------------
    if method == "tools/list":
        return _jsonrpc_response(req_id, {"tools": TOOLS})

    # -- tools/call --------------------------------------------------------
    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        log(f"Calling tool: {tool_name}")
        try:
            text = handle_tool_call(tool_name, arguments)
            return _jsonrpc_response(req_id, {
                "content": [{"type": "text", "text": text}],
            })
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            log(f"HTTP error calling {tool_name}: {exc.response.status_code} {body}")
            return _jsonrpc_response(req_id, {
                "content": [{"type": "text", "text": f"API error {exc.response.status_code}: {body}"}],
                "isError": True,
            })
        except httpx.ConnectError:
            msg = f"Cannot connect to Manor API at {MANOR_API}. Is the server running?"
            log(msg)
            return _jsonrpc_response(req_id, {
                "content": [{"type": "text", "text": msg}],
                "isError": True,
            })
        except Exception as exc:
            log(f"Error calling tool {tool_name}: {exc}\n{traceback.format_exc()}")
            return _jsonrpc_response(req_id, {
                "content": [{"type": "text", "text": f"Error: {exc}"}],
                "isError": True,
            })

    # -- ping --------------------------------------------------------------
    if method == "ping":
        return _jsonrpc_response(req_id, {})

    # -- unknown method ----------------------------------------------------
    return _jsonrpc_error(req_id, -32601, f"Method not found: {method}")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main() -> None:
    log(f"Starting MCP server (Manor API: {MANOR_API})")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            err = _jsonrpc_error(None, -32700, f"Parse error: {exc}")
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()
            continue

        try:
            response = handle_request(request)
        except Exception as exc:
            log(f"Unhandled error: {exc}\n{traceback.format_exc()}")
            response = _jsonrpc_error(
                request.get("id"),
                -32603,
                f"Internal error: {exc}",
            )

        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()

    log("stdin closed, shutting down.")


if __name__ == "__main__":
    main()
