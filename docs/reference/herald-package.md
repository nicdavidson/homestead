# Herald Package Reference

Herald is the Telegram bot interface for Homestead. It manages conversations, sessions, and routes messages to Claude/Grok models.

---

## Installation

```bash
pip install -e packages/herald
```

---

## Configuration

Set these environment variables (or create `.env` file):

```bash
# Required
TELEGRAM_BOT_TOKEN=your-bot-token-from-botfather
TELEGRAM_ALLOWED_USERS=123456789,987654321  # Comma-separated user IDs

# Optional
HOMESTEAD_DATA_DIR=~/.homestead
ANTHROPIC_API_KEY=your-key  # For Claude models
XAI_API_KEY=your-key        # For Grok
```

---

## Running

```bash
# Direct command
herald

# Or via Python module
python -m herald.main

# With auto-reload (requires watchdog)
watchmedo auto-restart --directory packages/herald/herald --pattern "*.py" --recursive -- python -m herald.main
```

You should see:
```
[herald] Watchtower logging enabled
[herald] Herald is running (active session: default)
[aiogram] Start polling
```

---

## Commands

### Session Management

- `/start` - Initialize bot
- `/sessions` - List all sessions
- `/session <name>` - Switch to session
- `/new <name>` - Create new session
- `/rename <old> <new>` - Rename session
- `/delete <name>` - Delete session

### Model Selection

- `/model` - Show current model
- `/model sonnet` - Switch to Claude Sonnet
- `/model opus` - Switch to Claude Opus
- `/model haiku` - Switch to Claude Haiku
- `/model grok` - Switch to Grok

### System Commands

- `/help` - Show help message
- `/reset` - Clear current session history
- `/stats` - Show usage statistics
- `/version` - Show Herald version

---

## Architecture

```
Telegram API
     ↓
aiogram (bot framework)
     ↓
herald/bot.py (message handlers)
     ↓
herald/providers.py (model routing)
     ↓
herald/claude.py (Claude CLI) | herald/grok.py (xAI API)
     ↓
herald/sessions.py (state management)
```

---

## Key Modules

### bot.py

Main bot logic and message handlers.

**Key functions:**
- `handle_message(message)` - Process user messages
- `handle_voice(message)` - Process voice messages
- `stream_response()` - Stream AI responses with progressive updates
- `trigger_reflection()` - Background reflection system

### providers.py

Model routing and provider management.

**Supported providers:**
- `claude` - Claude Sonnet (default)
- `opus` - Claude Opus
- `haiku` - Claude Haiku
- `grok` - Grok via xAI API

**Model mapping:**
```python
_CLI_MODELS = {
    "claude": None,  # Uses default
    "sonnet": "claude-sonnet-4-5-20250929",
    "opus": "claude-opus-4-5-20251101",
    "haiku": "claude-haiku-4-20250514",
}
```

### claude.py

Claude CLI subprocess handling.

**Key function:**
```python
def dispatch_message(
    session: Session,
    message: str,
    system_prompt: str = None,
    max_turns: int = 10
) -> str:
    """Send message to Claude CLI and stream response."""
```

**Features:**
- Subprocess management
- Streaming output parsing
- Session history injection
- Custom system prompts

### sessions.py

Session state management.

**Session structure:**
```python
class Session:
    session_id: str
    chat_id: str
    model: str
    messages: list[Message]
    created_at: datetime
    updated_at: datetime
```

**Key functions:**
- `create_session(chat_id, session_id, model)`
- `get_session(chat_id, session_id)`
- `add_message(session_id, role, content)`
- `get_history(session_id, limit=50)`
- `list_sessions(chat_id)`

### prompt.py

System prompt construction.

**Loads from:**
- `lore/soul.md` - Core identity
- `lore/claude.md` - Behavior directives
- `lore/user.md` - User context
- `lore/agents.md` - Agent coordination
- Skills (optional)

**Function:**
```python
def build_system_prompt(include_skills: bool = False) -> str:
    """Build complete system prompt from lore files."""
```

### queue.py

Outbox polling for cross-package messages.

**Background task:**
```python
async def poll_outbox():
    """Poll outbox every 2 seconds and send pending messages."""
    while True:
        messages = get_pending()
        for msg in messages:
            await send_to_telegram(msg)
        await asyncio.sleep(2)
```

---

## Database Schema

**Location:** `~/.homestead/herald/sessions.db`

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    chat_id TEXT NOT NULL,
    model TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);
```

---

## Telegram HTML Formatting

Herald converts markdown to Telegram HTML. Supported tags:

- `<b>` - Bold
- `<i>` - Italic
- `<code>` - Inline code
- `<pre>` - Code block
- `<a href="...">` - Links
- `<u>` - Underline
- `<s>`, `<strike>`, `<del>` - Strikethrough

**Unsupported tags are stripped.**

**Conversion function:** `md_to_telegram_html()` in `bot.py`

---

## Reflection System

Herald implements automatic reflections:

**Trigger conditions:**
- After 5+ messages in session
- Minimum 15 minutes since last reflection
- Uses Haiku model (cost: ~$0.0004 per reflection)

**Process:**
1. Copy session with forced Haiku model
2. Dispatch reflection prompt in background thread
3. Save to `~/.homestead/journal/YYYY-MM-DD.md`
4. Don't wait for completion

**Configuration:**
```python
_REFLECTION_COOLDOWN_SECONDS = 900  # 15 minutes
_REFLECTION_MIN_MESSAGES = 5
```

---

## Voice Message Support

Herald can transcribe voice messages if configured:

**Requirements:**
- Whisper model installed (not included by default)

**Process:**
1. Download voice file from Telegram
2. Convert to format Whisper accepts
3. Transcribe
4. Process as text message

---

## Middleware

Herald uses custom middleware for:

**Authentication (auth.py):**
- Check user ID against allowlist
- Reject unauthorized users

**Logging (middleware.py):**
- Log all incoming updates
- Track message processing time

---

## Error Handling

Herald logs all errors to Watchtower:

```python
from common.watchtower import Watchtower

logger = Watchtower(service="herald")
logger.error("Error processing message", error=str(e), chat_id=chat_id)
```

**Common errors:**
- Telegram API rate limits
- Claude CLI timeouts
- Session database locks
- Markdown parsing failures

---

## Usage Tracking

Herald tracks token usage in `~/.homestead/usage.db`:

```python
# Log usage after each message
log_usage(
    model="sonnet",
    input_tokens=1234,
    output_tokens=5678,
    session_id=session.session_id
)
```

**Query usage:**
```python
from herald.usage import get_usage_stats

stats = get_usage_stats(since="2026-01-01")
```

---

## Development

### Adding a New Command

1. Add handler in `bot.py`:
```python
@dp.message(Command("mycommand"))
async def handle_mycommand(message: Message):
    await message.answer("Response")
```

2. Register command in bot initialization

3. Add to help text

### Adding a New Model Provider

1. Implement in `providers.py`:
```python
def dispatch_to_my_model(session, message):
    # Call model API
    # Return response
```

2. Add to `PROVIDER_MAP`

3. Add to `/model` command handler

---

## Testing

```bash
# Run Herald tests
pytest packages/herald/tests/

# Test specific module
pytest packages/herald/tests/test_sessions.py
```

---

## Troubleshooting

### Bot doesn't respond

Check:
- `TELEGRAM_BOT_TOKEN` is set
- User ID is in `TELEGRAM_ALLOWED_USERS`
- Herald process is running
- Check logs: `tail -f ~/.homestead/herald.log`

### "Session not found" error

Create new session: `/new default`

### Model not working

Check:
- Claude CLI installed: `which claude`
- API key set (for Grok): `echo $XAI_API_KEY`
- Model name correct: `/model sonnet`

### Messages stuck in outbox

Check:
- Outbox polling is running (background thread)
- No database lock issues
- Query outbox: `sqlite3 ~/.homestead/outbox.db "SELECT * FROM messages WHERE status='pending'"`

---

**Last Updated:** 2026-01-31
