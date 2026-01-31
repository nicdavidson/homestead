# Manor

**The Homestead web dashboard.**

Manor is the web interface for the Homestead platform. It provides a browser-based dashboard for chat, session management, log viewing, task tracking, job scheduling, skills editing, lore management, and system configuration. The frontend is a Next.js application; the backend is a FastAPI server that bridges the frontend to the shared Homestead infrastructure.

---

## Architecture

```
Browser  <-->  Next.js (port 3000)  <-->  FastAPI (port 8700)  <-->  ~/.homestead/
               TypeScript + React          Python                     SQLite DBs
               Tailwind CSS                WebSockets (chat)          Markdown files
```

The Next.js frontend communicates with the FastAPI backend over HTTP and WebSockets. The backend reads from and writes to the same SQLite databases and filesystem paths used by Herald and the other Homestead packages. This means changes made in Manor are immediately visible to the Telegram bot, and vice versa.

### Frontend Pages

| Route | Purpose |
|---|---|
| `/` | Home / overview |
| `/chat` | Chat interface with Claude (WebSocket streaming) |
| `/sessions` | Browse and manage Herald conversation sessions |
| `/logs` | Watchtower log viewer with filtering |
| `/tasks` | Steward task management |
| `/jobs` | Almanac job scheduling |
| `/skills` | Skills editor (markdown files) |
| `/lore` | Lore viewer and editor |
| `/scratchpad` | Scratchpad file browser |
| `/config` | System configuration panel |

### API Routers

| Router | Prefix | Description |
|---|---|---|
| `chat` | `/chat` | WebSocket chat with Claude CLI |
| `sessions` | `/sessions` | Session CRUD and history |
| `logs` | `/logs` | Watchtower log queries |
| `tasks` | `/tasks` | Steward task operations |
| `skills` | `/skills` | Skill file read/write |
| `lore` | `/lore` | Lore file read/write |
| `scratchpad` | `/scratchpad` | Scratchpad file management |
| `config_routes` | `/config` | System configuration |

---

## Setup

### Prerequisites

- Node.js 20+
- npm
- Python 3.11+
- pip
- The `homestead-common` package installed (`pip install -e ../packages/common`)

### Install frontend dependencies

```bash
cd manor
npm install
```

### Install backend dependencies

```bash
pip install -r manor/api/requirements.txt
```

The backend depends on:
- `fastapi` >= 0.115
- `uvicorn[standard]` >= 0.32
- `python-dotenv` >= 1.0
- `websockets` >= 13.0

### Environment configuration

Create a `.env` file in the project root or set these environment variables:

```bash
# Required
HOMESTEAD_DATA_DIR=~/.homestead      # Root data directory

# Optional -- auto-detected from repo structure if unset
HERALD_DATA_DIR=                      # Herald session database directory
LORE_DIR=                             # Path to lore/ identity files

# Optional -- defaults shown
MANOR_PORT=8700                       # FastAPI backend port
ALLOWED_ORIGINS=http://localhost:3000  # CORS origins (comma-separated)
CLAUDE_CLI_PATH=claude                # Path to Claude CLI binary
CLAUDE_TIMEOUT_S=300                  # Claude response timeout (seconds)
MAX_TURNS=10                          # Max conversation turns per request
```

If `HERALD_DATA_DIR` and `LORE_DIR` are not set, the API will attempt to auto-detect them relative to the repository structure. This works out of the box for standard development setups.

---

## Development

### Running the dev servers

You need two terminal sessions -- one for the API backend and one for the Next.js frontend.

**Terminal 1 -- API backend:**

```bash
# From the repo root
uvicorn manor.api.main:app --port 8700 --reload
```

Or equivalently:

```bash
python -m manor.api.main
```

The API serves on [http://localhost:8700](http://localhost:8700). The `--reload` flag enables auto-restart on file changes.

**Terminal 2 -- Next.js frontend:**

```bash
cd manor
npm run dev
```

The frontend serves on [http://localhost:3000](http://localhost:3000).

### Verifying the setup

Once both servers are running:

1. Open [http://localhost:3000](http://localhost:3000) -- you should see the Manor dashboard.
2. Check the API health endpoint at [http://localhost:8700/health](http://localhost:8700/health) -- it should return `{"status": "ok", "service": "manor-api"}`.
3. The chat page requires the Claude CLI to be installed and accessible at the path specified by `CLAUDE_CLI_PATH`.

### Building for production

```bash
cd manor
npm run build
npm run start
```

This compiles the Next.js app and starts it in production mode on port 3000.

### Project structure

```
manor/
  api/
    __init__.py
    main.py              # FastAPI app entrypoint
    config.py            # Settings loaded from environment
    routers/
      __init__.py
      chat.py            # WebSocket chat with Claude
      sessions.py        # Session management
      logs.py            # Watchtower log queries
      tasks.py           # Steward task routes
      skills.py          # Skill file routes
      lore.py            # Lore file routes
      scratchpad.py      # Scratchpad file routes
      config_routes.py   # System config routes
  src/
    app/                 # Next.js App Router pages
      layout.tsx         # Root layout
      page.tsx           # Home page
      chat/              # Chat interface
      sessions/          # Session browser
      logs/              # Log viewer
      tasks/             # Task management
      jobs/              # Job scheduling
      skills/            # Skills editor
      lore/              # Lore editor
      scratchpad/        # Scratchpad browser
      config/            # Configuration panel
    components/          # Shared React components
    lib/                 # Client-side utilities
    styles/              # CSS and Tailwind styles
  package.json
  next.config.ts
  tsconfig.json
```

### Adding a new page

1. Create a directory under `src/app/` with a `page.tsx`.
2. If the page needs backend data, create a router file under `api/routers/`.
3. Register the new router in `api/main.py` by importing it and calling `app.include_router()`.
4. Add a navigation link in the layout or sidebar component.

### Tech stack

| Component | Technology |
|---|---|
| Frontend framework | Next.js 15, React 19 |
| Language | TypeScript 5 |
| Styling | Tailwind CSS 4 |
| Backend framework | FastAPI |
| Server | Uvicorn with WebSocket support |
| Real-time | WebSockets for chat streaming |
| Data layer | SQLite databases + filesystem (shared with other Homestead packages) |
