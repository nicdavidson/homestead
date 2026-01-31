# Homestead

**A self-sufficient AI infrastructure framework.**

Homestead is a personal monorepo of Python packages and a web dashboard that together form an autonomous AI assistant platform. Themed around the concept of a homestead -- a self-sufficient home -- each package is a building on the property, serving a distinct role in the system.

---

## Architecture

```
                          +---------------------+
                          |        lore/        |
                          |  Identity & persona |
                          |  (soul, directives, |
                          |   triggers, user)   |
                          +----------+----------+
                                     |
               reads personality     |
        +----------------------------+----------------------------+
        |                            |                            |
        v                            v                            v
+-------+--------+      +-----------+-----------+      +---------+---------+
|     herald      |      |         manor         |      |       hearth      |
|  Telegram bot   |      |    Web dashboard      |      |   AI personality  |
|  (aiogram)      |      |  Next.js + FastAPI    |      |      layer        |
+-------+--------+      +-----------+-----------+      +-------------------+
        |                            |
        |   +------------------------+
        |   |
        v   v
+-------+---+--------+
|        common       |
|  watchtower (logs)  |
|  outbox (messages)  |
|  skills / models    |
+-------+---+--------+
        |   |
        v   v
+-------+--------+      +-------------------+
|     steward     |      |      almanac      |
| Task management |      |  Job scheduling   |
+-----------------+      +-------------------+

Data at rest: ~/.homestead/
  watchtower.db    structured logs (SQLite)
  outbox.db        pending messages (SQLite)
  skills/          shared skill library (markdown)
  scratchpad/      persistent AI memory (markdown)
```

All packages share data through SQLite databases and the filesystem under `~/.homestead/`. Herald and Manor are the two primary interfaces -- Telegram and web, respectively -- while Common provides the shared infrastructure they both depend on.

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+ and npm
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- Claude CLI installed, or a xAI API key for Grok

### Clone and install

```bash
git clone <repo-url> homestead
cd homestead
```

### Set up the Python packages

Each package under `packages/` is installable via pip. Install them in development mode:

```bash
pip install -e packages/common
pip install -e packages/herald
pip install -e packages/steward
pip install -e packages/almanac
```

### Configure environment

Create a `.env` file in the project root (or in each package directory):

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_ALLOWED_USERS=123456789  # comma-separated Telegram user IDs

# Data directories
HOMESTEAD_DATA_DIR=~/.homestead

# xAI / Grok (optional)
XAI_API_KEY=your-xai-api-key

# Manor
MANOR_PORT=8700
ALLOWED_ORIGINS=http://localhost:3000
CLAUDE_CLI_PATH=claude
```

### Run Herald (Telegram bot)

```bash
herald
# or: python -m herald.main
```

### Run Manor (web dashboard)

The dashboard has two processes -- a Next.js frontend and a FastAPI backend:

```bash
# Terminal 1: API backend
cd manor
uvicorn manor.api.main:app --port 8700 --reload

# Terminal 2: Next.js frontend
cd manor
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Packages

### common (homestead-common)

Shared infrastructure that all other packages depend on.

- **Watchtower** -- Structured SQLite logging. Every significant event across the system is recorded and queryable, including by the AI itself.
- **Outbox** -- Cross-package message delivery. Any package can enqueue a message for Telegram delivery; Herald picks it up and sends it.
- **Skills** -- Shared skill library stored as markdown files at `~/.homestead/skills/`. Skills are readable by any package and editable through Manor.
- **Models** -- Shared data models and type definitions.
- **DB** -- Common SQLite connection and migration utilities.

### herald

Telegram bot interface built on aiogram.

- Multi-session support with persistent conversation history
- Model switching between Claude (via CLI) and Grok (via xAI API)
- Streaming responses delivered as progressive Telegram message edits
- Multi-agent visibility: subagents (nightshift, researcher, etc.) can speak in chat with distinct identity formatting
- Authentication via allowed-user list
- Outbox polling for cross-package message delivery

### steward

Task management system for autonomous and human-directed work.

- Task creation with priorities, status tracking, and descriptions
- Blocker and dependency modeling
- Persistent SQLite storage
- Queryable from Herald, Manor, and the AI itself

### almanac

Job scheduling with multiple trigger types.

- Cron expressions for recurring jobs
- Interval-based scheduling
- One-time triggers for deferred execution
- Persistent job store in SQLite

### hearth

AI entity personality layer. Hearth is the more fully featured personality and agent framework, with support for:

- Agent definitions and routing
- Nightshift and background processing
- Homestead integration hooks
- Service management and systemd support
- Web interface components

### manor

Web dashboard for managing the entire homestead. See [manor/README.md](manor/README.md) for detailed setup.

- Chat interface with Claude via WebSocket streaming
- Session browser and management
- Watchtower log viewer with filtering
- Task management UI (Steward)
- Job scheduling UI (Almanac)
- Skills editor
- Lore viewer and editor
- Scratchpad file browser
- System configuration panel

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `HOMESTEAD_DATA_DIR` | `~/.homestead` | Root data directory for databases, skills, scratchpad |
| `TELEGRAM_BOT_TOKEN` | -- | Telegram bot token from BotFather |
| `TELEGRAM_ALLOWED_USERS` | -- | Comma-separated Telegram user IDs |
| `XAI_API_KEY` | -- | xAI API key for Grok model access |
| `HERALD_DATA_DIR` | auto-detected | Herald session database directory |
| `LORE_DIR` | auto-detected | Path to lore/ identity files |
| `CLAUDE_CLI_PATH` | `claude` | Path to Claude CLI binary |
| `CLAUDE_TIMEOUT_S` | `300` | Claude CLI response timeout in seconds |
| `MAX_TURNS` | `10` | Maximum conversation turns per request |
| `MANOR_PORT` | `8700` | FastAPI backend port |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS origins for Manor API |

### Lore Files

The `lore/` directory contains identity and behavior files that shape the AI's personality:

| File | Purpose |
|---|---|
| `soul.md` | Core entity identity, principles, and values |
| `claude.md` | Behavior directives: tone, anti-sycophancy rules, response style |
| `user.md` | User context and preferences (gitignored -- create from `user.md.example`) |
| `triggers.md` | Proactive trigger architecture for autonomous behavior |

To get started, copy the example user file:

```bash
cp lore/user.md.example lore/user.md
```

Then edit `lore/user.md` with your personal context.

---

## Customization

Homestead is designed to be personalized. The three main surfaces for customization are lore, skills, and the scratchpad.

### Lore (Identity)

Edit the files in `lore/` to shape how the AI behaves. `soul.md` defines who the entity is. `claude.md` provides concrete behavioral directives -- this is where anti-sycophancy rules, formatting preferences, and communication style are defined. `user.md` gives the AI context about you.

### Skills

Skills are markdown files stored at `~/.homestead/skills/`. Each file describes a capability or procedure the AI can reference. Add new skills by creating `.md` files in that directory, or use the Manor skills editor.

Example skill file (`~/.homestead/skills/git-workflow.md`):

```markdown
# Git Workflow

When committing changes:
1. Use conventional commit messages
2. Keep commits atomic
3. Always run tests before pushing
```

### Scratchpad

The scratchpad at `~/.homestead/scratchpad/` is persistent AI memory. The AI can read and write files here to remember context across sessions. You can also place files here manually for the AI to reference.

---

## Development

### Repository Structure

```
homestead/
  lore/                    # AI identity files
  manor/                   # Web dashboard
    api/                   # FastAPI backend (Python)
      routers/             # API route handlers
      config.py            # Settings from environment
      main.py              # App entrypoint
    src/                   # Next.js frontend (TypeScript)
      app/                 # App router pages
      components/          # React components
      lib/                 # Client utilities
      styles/              # CSS / Tailwind
    package.json
    next.config.ts
    tsconfig.json
  packages/
    common/                # Shared infrastructure
      common/
        watchtower.py      # Structured logging
        outbox.py          # Message delivery
        skills.py          # Skill file management
        models.py          # Shared data models
        db.py              # SQLite utilities
    herald/                # Telegram bot
      herald/
        bot.py             # Bot setup and handlers
        claude.py          # Claude CLI integration
        providers.py       # Model provider abstraction
        sessions.py        # Session management
        prompt.py          # System prompt construction
        queue.py           # Message queue
        auth.py            # User authentication
        config.py          # Herald settings
        main.py            # Entrypoint
    steward/               # Task management
      steward/
        models.py          # Task data models
        store.py           # SQLite persistence
        main.py            # Entrypoint
    almanac/               # Job scheduling
      almanac/
        models.py          # Job data models
        store.py           # SQLite persistence
        scheduler.py       # Scheduling engine
        main.py            # Entrypoint
    hearth/                # AI personality layer
```

### Adding a New Package

1. Create a directory under `packages/` with a `pyproject.toml`:

```toml
[project]
name = "your-package"
version = "0.1.0"
description = "Description of your package"
requires-python = ">=3.11"
dependencies = []

[project.scripts]
your-package = "your_package.main:main"
```

2. Create a Python package directory with `__init__.py` and `main.py`.
3. Install in development mode: `pip install -e packages/your-package`
4. If it needs logging, import and use Watchtower from `common`.
5. If it needs to send Telegram messages, use the Outbox from `common`.

### Patterns

- **SQLite for persistence.** Every package that stores state uses SQLite. No external database servers.
- **Filesystem for content.** Skills, scratchpad, and lore are plain markdown files on disk.
- **Environment for config.** All configuration flows through environment variables, loaded via `python-dotenv`.
- **Anti-sycophancy by design.** The system prompt explicitly instructs against flattery, hedging, and unnecessary affirmation. This is a core design principle, not a setting.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Telegram bot | Python 3.11+, aiogram 3 |
| Web frontend | Next.js 15, React 19, TypeScript, Tailwind CSS 4 |
| Web backend | FastAPI, Uvicorn, WebSockets |
| AI providers | Claude (CLI), Grok (xAI REST API) |
| Database | SQLite (via standard library) |
| Content | Markdown files on disk |
| Scheduling | Python asyncio, cron expressions |

---

## License

Personal project. Not currently licensed for redistribution.
