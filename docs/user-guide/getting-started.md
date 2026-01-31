# Getting Started with Homestead

**Welcome to Homestead!** This guide will help you install and configure your autonomous AI assistant platform.

---

## What is Homestead?

Homestead is a self-sufficient AI infrastructure framework that combines:
- **Herald** - Telegram bot interface for mobile access
- **Manor** - Web dashboard for management and configuration
- **Steward** - Task management system
- **Almanac** - Job scheduling
- **Memory system** - Persistent learning across sessions

All components share data through SQLite databases and markdown files in `~/.homestead/`.

---

## Prerequisites

Before installing, ensure you have:

- **Python 3.11+** installed
- **Node.js 20+** and npm installed
- **Telegram bot token** from [@BotFather](https://t.me/BotFather)
- **Claude CLI** installed (or xAI API key for Grok model)

### Get a Telegram Bot Token

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Choose a name and username for your bot
4. Save the bot token (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Get Your Telegram User ID

1. Message [@userinfobot](https://t.me/userinfobot)
2. It will reply with your user ID (a number like `123456789`)
3. Save this ID for configuration

---

## Installation

### 1. Clone the Repository

```bash
git clone <repo-url> homestead
cd homestead
```

### 2. Install Python Packages

Install all packages in development mode:

```bash
pip install -e packages/common
pip install -e packages/herald
pip install -e packages/steward
pip install -e packages/almanac
```

### 3. Install Manor Dependencies

```bash
cd manor
npm install
cd ..
```

---

## Configuration

### Create Environment File

Create a `.env` file in the project root:

```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your-bot-token-from-botfather
TELEGRAM_ALLOWED_USERS=your-telegram-user-id

# Data Directory (where databases and files are stored)
HOMESTEAD_DATA_DIR=~/.homestead

# Optional: xAI/Grok API
XAI_API_KEY=your-xai-api-key

# Manor Web Dashboard
MANOR_PORT=8700
ALLOWED_ORIGINS=http://localhost:3000

# Claude CLI
CLAUDE_CLI_PATH=claude
CLAUDE_TIMEOUT_S=300
MAX_TURNS=10
```

**Important:** Replace the placeholder values with your actual credentials.

### Set Up Lore (Identity Files)

Lore files define your AI's personality and behavior. Copy the example user file:

```bash
cp lore/user.md.example lore/user.md
```

Then edit `lore/user.md` with your personal information:

```markdown
# User Profile

## Name
Milo

## Context
[Add information about yourself that helps the AI serve you better]

## Preferences
- Communication style: Direct and concise
- Timezone: PST
- Primary use cases: Development, research, task management
```

The other lore files (`soul.md`, `claude.md`, `triggers.md`, `agents.md`) define the AI's core identity and can be customized later.

---

## Running Homestead

### Start Herald (Telegram Bot)

Open a terminal and run:

```bash
herald
# or: python -m herald.main
```

You should see:
```
[herald] Watchtower logging enabled
[herald] Herald is running (active session: default)
[aiogram] Start polling
```

### Start Manor (Web Dashboard)

Manor has two components that run simultaneously.

**Terminal 1 - API Backend:**
```bash
cd manor
uvicorn api.main:app --port 8700 --reload
```

**Terminal 2 - Frontend:**
```bash
cd manor
npm run dev
```

Open your browser to [http://localhost:3000](http://localhost:3000)

---

## First Steps

### 1. Test Telegram Bot

1. Open Telegram
2. Find your bot (search for the username you chose with BotFather)
3. Send `/start` or any message
4. The bot should respond!

**Common commands:**
- `/new` - Start a fresh conversation
- `/status` - Show session info
- `/session <name>` - Switch/create named session
- `/model <model>` - Change AI model (sonnet, opus, haiku, grok)
- `/help` - Show all commands

### 2. Explore Manor Dashboard

Visit [http://localhost:3000](http://localhost:3000) and explore:

- **Chat** - Web-based conversation interface
- **Tasks** - View and manage tasks (Steward)
- **Jobs** - Schedule recurring jobs (Almanac)
- **Skills** - View and edit skill library
- **Lore** - Edit identity files
- **Scratchpad** - Browse persistent memory
- **Logs** - View system logs (Watchtower)

### 3. Try Basic Commands

**In Telegram or Manor chat, try:**

```
Hello! Can you tell me about yourself?
```

The AI will introduce itself based on `lore/soul.md`.

```
What can you help me with?
```

Learn about available capabilities.

```
Create a task: Set up development environment
```

This creates a task in Steward (view in Manor → Tasks).

---

## Understanding Sessions

Homestead supports **multiple named sessions** for different contexts:

### Session Commands

```
/session work          # Switch to (or create) "work" session
/session personal      # Switch to "personal" session
/sessions              # List all sessions
```

Each session:
- Has independent conversation history
- Can use a different AI model
- Persists across restarts

### Session Management

- **View current session:** `/status`
- **Start fresh conversation (same session):** `/new`
- **Change model:** `/model haiku` (or sonnet, opus, grok)

---

## Configuration

### Runtime Configuration

Some settings can be changed without restarting:

**Via Manor:** Configuration panel (coming soon)

**Via API:** POST to `/api/config`

**Editable settings:**
- `allowed_models` - Which AI models are available
- `max_turns` - Maximum conversation turns per request
- `claude_timeout_s` - Timeout for Claude CLI responses
- `proposal_test_cmd` - Command to run before applying code proposals

### Environment Variables

Full list of configuration options:

| Variable | Default | Purpose |
|----------|---------|---------|
| `HOMESTEAD_DATA_DIR` | `~/.homestead` | Root data directory |
| `TELEGRAM_BOT_TOKEN` | (required) | Bot token from BotFather |
| `TELEGRAM_ALLOWED_USERS` | (required) | Comma-separated user IDs |
| `XAI_API_KEY` | (optional) | For Grok model access |
| `CLAUDE_CLI_PATH` | `claude` | Path to Claude CLI binary |
| `CLAUDE_TIMEOUT_S` | `300` | Response timeout (seconds) |
| `MAX_TURNS` | `10` | Max conversation turns |
| `MANOR_PORT` | `8700` | API backend port |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS origins |

---

## Data Storage

All Homestead data lives in `~/.homestead/`:

```
~/.homestead/
├── journal/           # Daily reflections (auto-generated)
├── scratchpad/        # Persistent memory notes
├── skills/            # Skill library (markdown)
├── lore/              # (symlink to repo lore/)
├── usage.db           # Token usage tracking
├── watchtower.db      # System logs
├── outbox.db          # Message queue
├── steward/
│   └── tasks.db       # Tasks
└── almanac/
    └── jobs.db        # Scheduled jobs
```

### Backup Your Data

See [Backup & Migration Strategy](../roadmaps/backup-and-migration-strategy.md) for details on backing up your data before server migrations.

**Critical files to backup:**
- `~/.homestead/journal/` - Your reflection history
- `~/.homestead/scratchpad/` - Persistent memory
- `~/.homestead/skills/` - Custom skills
- `~/.homestead/usage.db` - Token usage history
- `~/.homestead/steward/tasks.db` - Active tasks

---

## Troubleshooting

### Herald Not Starting

**Error:** `ModuleNotFoundError: No module named 'herald'`

**Fix:** Install Herald package:
```bash
pip install -e packages/herald
```

**Error:** `Telegram server says - Unauthorized`

**Fix:** Check `TELEGRAM_BOT_TOKEN` in `.env` file.

### Manor Not Loading

**Error:** `Connection refused on port 8700`

**Fix:** Ensure API backend is running:
```bash
cd manor
uvicorn api.main:app --port 8700
```

**Error:** `Module not found` in Next.js

**Fix:** Install dependencies:
```bash
cd manor
npm install
```

### Permission Errors

**Error:** `Permission denied: ~/.homestead/`

**Fix:** Create directory with correct permissions:
```bash
mkdir -p ~/.homestead
chmod 755 ~/.homestead
```

### Claude CLI Not Found

**Error:** `FileNotFoundError: claude`

**Fix:** Install Claude CLI or set `CLAUDE_CLI_PATH` to correct location:
```bash
# If installed globally:
export CLAUDE_CLI_PATH=/usr/local/bin/claude

# If installed via npm:
export CLAUDE_CLI_PATH=~/.npm-global/bin/claude
```

---

## Next Steps

Now that Homestead is running:

1. **Customize your identity** - Edit `lore/user.md`, `lore/soul.md`
2. **Explore the memory system** - See [Memory Roadmap](../roadmaps/memory-roadmap.md)
3. **Learn about governance** - Read [Governance Priorities](../roadmaps/governance-priorities.md)
4. **Set up tasks** - Create your first tasks in Steward
5. **Schedule jobs** - Set up recurring jobs in Almanac

---

## Getting Help

- **Documentation:** See [START_HERE.md](../START_HERE.md) for full doc navigation
- **Architecture:** Read [Architecture Overview](../architecture/overview.md)
- **Contributing:** See [CONTRIBUTING.md](../../CONTRIBUTING.md)

---

**Last Updated:** 2026-01-31
