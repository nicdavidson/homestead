"""MCP server for Telegram — send files, photos, and messages.

Reads TG_BOT_TOKEN and TG_CHAT_ID from the environment (set by Herald
per-spawn) and exposes tools that call the Telegram Bot API directly.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "mcp-tg"
SERVER_VERSION = "0.1.0"

BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TG_CHAT_ID", "")
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def log(msg: str) -> None:
    print(f"[mcp-tg] {msg}", file=sys.stderr, flush=True)


def _client() -> httpx.Client:
    return httpx.Client(timeout=60.0)


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "send_message",
        "description": "Send a text message to the current Telegram chat.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Message text to send.",
                },
                "parse_mode": {
                    "type": "string",
                    "description": "Optional parse mode: Markdown, MarkdownV2, or HTML.",
                    "enum": ["Markdown", "MarkdownV2", "HTML"],
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "send_photo",
        "description": "Send a photo (image file) to the current Telegram chat.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the image file to send.",
                },
                "caption": {
                    "type": "string",
                    "description": "Optional caption for the photo.",
                },
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "send_file",
        "description": "Send a document/file to the current Telegram chat.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the file to send.",
                },
                "caption": {
                    "type": "string",
                    "description": "Optional caption for the file.",
                },
            },
            "required": ["file_path"],
        },
    },
]

# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


def _require_config() -> None:
    if not BOT_TOKEN:
        raise ValueError("TG_BOT_TOKEN not set")
    if not CHAT_ID:
        raise ValueError("TG_CHAT_ID not set")


def handle_tool_call(tool_name: str, arguments: dict) -> str:
    _require_config()

    if tool_name == "send_message":
        return _send_message(arguments)
    elif tool_name == "send_photo":
        return _send_photo(arguments)
    elif tool_name == "send_file":
        return _send_file(arguments)
    else:
        raise ValueError(f"Unknown tool: {tool_name}")


def _send_message(args: dict) -> str:
    text = args.get("text", "")
    if not text:
        return "Error: text is required"

    data: dict = {"chat_id": CHAT_ID, "text": text}
    parse_mode = args.get("parse_mode")
    if parse_mode:
        data["parse_mode"] = parse_mode

    with _client() as client:
        resp = client.post(f"{TG_API}/sendMessage", json=data)
        resp.raise_for_status()

    log(f"sent message to chat {CHAT_ID} ({len(text)} chars)")
    return f"Message sent ({len(text)} chars)"


def _send_photo(args: dict) -> str:
    file_path = args.get("file_path", "")
    if not file_path:
        return "Error: file_path is required"

    path = Path(file_path)
    if not path.is_file():
        return f"Error: file not found: {file_path}"

    caption = args.get("caption", "")

    with _client() as client:
        with open(path, "rb") as f:
            files = {"photo": (path.name, f, _mime_type(path))}
            data: dict = {"chat_id": CHAT_ID}
            if caption:
                data["caption"] = caption
            resp = client.post(f"{TG_API}/sendPhoto", data=data, files=files)
            resp.raise_for_status()

    size = path.stat().st_size
    log(f"sent photo to chat {CHAT_ID}: {path.name} ({size} bytes)")
    return f"Photo sent: {path.name} ({size} bytes)"


def _send_file(args: dict) -> str:
    file_path = args.get("file_path", "")
    if not file_path:
        return "Error: file_path is required"

    path = Path(file_path)
    if not path.is_file():
        return f"Error: file not found: {file_path}"

    caption = args.get("caption", "")

    with _client() as client:
        with open(path, "rb") as f:
            files = {"document": (path.name, f, _mime_type(path))}
            data: dict = {"chat_id": CHAT_ID}
            if caption:
                data["caption"] = caption
            resp = client.post(f"{TG_API}/sendDocument", data=data, files=files)
            resp.raise_for_status()

    size = path.stat().st_size
    log(f"sent file to chat {CHAT_ID}: {path.name} ({size} bytes)")
    return f"File sent: {path.name} ({size} bytes)"


def _mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".csv": "text/csv",
        ".json": "application/json",
    }.get(suffix, "application/octet-stream")


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
    req_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params", {})

    if method == "initialize":
        return _jsonrpc_response(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        })

    if method == "notifications/initialized":
        log("Client initialized.")
        return None

    if method == "notifications/cancelled":
        log(f"Request cancelled: {params}")
        return None

    if method == "tools/list":
        return _jsonrpc_response(req_id, {"tools": TOOLS})

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
            log(f"TG API error calling {tool_name}: {exc.response.status_code} {body}")
            return _jsonrpc_response(req_id, {
                "content": [{"type": "text", "text": f"Telegram API error {exc.response.status_code}: {body}"}],
                "isError": True,
            })
        except Exception as exc:
            log(f"Error calling tool {tool_name}: {exc}\n{traceback.format_exc()}")
            return _jsonrpc_response(req_id, {
                "content": [{"type": "text", "text": f"Error: {exc}"}],
                "isError": True,
            })

    if method == "ping":
        return _jsonrpc_response(req_id, {})

    return _jsonrpc_error(req_id, -32601, f"Method not found: {method}")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def main() -> None:
    log(f"Starting MCP server (chat_id={CHAT_ID}, token={'set' if BOT_TOKEN else 'MISSING'})")

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
