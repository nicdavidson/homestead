# Developer Setup Guide

This guide covers setting up a Homestead development environment.

---

## Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** installed
- **Node.js 20+** and npm installed
- **Git** for version control
- **Claude CLI** installed (or xAI API key for Grok)
- A code editor (VS Code recommended)

---

## Clone the Repository

```bash
git clone <repo-url> homestead
cd homestead
```

---

## Python Environment Setup

### Option 1: System Python

Install all packages in development mode:

```bash
pip install -e packages/common
pip install -e packages/herald
pip install -e packages/steward
pip install -e packages/almanac
pip install -e packages/mcp-homestead
```

### Option 2: Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows

# Install packages
pip install -e packages/common
pip install -e packages/herald
pip install -e packages/steward
pip install -e packages/almanac
pip install -e packages/mcp-homestead
```

### Verify Installation

```bash
# Test imports
python -c "from common.watchtower import Watchtower; print('✅ Common works')"
python -c "from herald.bot import main; print('✅ Herald works')"
python -c "from steward.store import TaskStore; print('✅ Steward works')"
```

---

## Node.js Environment Setup

Manor (the web dashboard) requires Node.js dependencies:

```bash
cd manor
npm install
cd ..
```

---

## Environment Configuration

Create a `.env` file in the project root:

```bash
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your-bot-token-from-botfather
TELEGRAM_ALLOWED_USERS=your-telegram-user-id

# Data Directory
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

# Auto-detected (optional)
HERALD_DATA_DIR=  # Auto-detected from repo if empty
LORE_DIR=         # Auto-detected from repo if empty
```

---

## Initialize Data Directory

Create the Homestead data directory structure:

```bash
mkdir -p ~/.homestead/{journal,scratchpad,skills,steward,almanac}
```

---

## Set Up Lore Files

Lore files define the AI's identity and behavior:

```bash
# Copy the example user file
cp lore/user.md.example lore/user.md

# Edit with your information
nano lore/user.md
```

The other lore files (`soul.md`, `claude.md`, `triggers.md`, `agents.md`) are ready to use as-is.

---

## Running in Development Mode

### Start Herald (Telegram Bot)

```bash
# Option 1: Direct command
herald

# Option 2: Python module
python -m herald.main

# Option 3: With auto-reload (requires watchdog)
watchmedo auto-restart --directory packages/herald/herald --pattern "*.py" --recursive -- python -m herald.main
```

You should see:
```
[herald] Watchtower logging enabled
[herald] Herald is running (active session: default)
[aiogram] Start polling
```

### Start Manor (Web Dashboard)

Manor requires two processes running simultaneously.

**Terminal 1 - API Backend:**
```bash
# From repo root
cd manor
uvicorn api.main:app --port 8700 --reload
```

**Terminal 2 - Frontend:**
```bash
# From manor directory
cd manor
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) to access Manor.

---

## Development Workflow

### Making Changes

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** to the relevant package(s)

3. **Test your changes** (see Testing Guide)

4. **Commit with conventional commits:**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

### Package Structure

Each package under `packages/` follows this structure:

```
packages/package-name/
├── package_name/           # Python package directory
│   ├── __init__.py
│   ├── main.py            # Entry point
│   └── *.py               # Other modules
├── pyproject.toml         # Package metadata and dependencies
└── README.md             # Package documentation
```

### Adding Dependencies

For Python packages, edit the `pyproject.toml`:

```toml
[project]
dependencies = [
    "new-package>=1.0.0",
]
```

Then reinstall:
```bash
pip install -e packages/package-name
```

For Manor (Node.js), use npm:
```bash
cd manor
npm install <package-name>
```

---

## Debugging

### Python Debugging

Use VS Code's built-in debugger or add breakpoints:

```python
import pdb; pdb.set_trace()  # Python debugger
```

### Herald Logging

Herald uses Watchtower for structured logging:

```python
from common.watchtower import Watchtower

logger = Watchtower(service="your-service")
logger.info("message", extra_field="value")
logger.error("error occurred", error=str(e))
```

View logs in Manor's Logs page or query directly:

```python
from common.watchtower import Watchtower

wt = Watchtower("debug")
logs = wt.query(service="herald", level="ERROR", limit=50)
```

### Manor API Debugging

The FastAPI backend includes automatic documentation:

- **OpenAPI docs:** [http://localhost:8700/docs](http://localhost:8700/docs)
- **ReDoc:** [http://localhost:8700/redoc](http://localhost:8700/redoc)

### Database Inspection

All data is stored in SQLite databases under `~/.homestead/`:

```bash
# Inspect sessions
sqlite3 ~/.homestead/herald/sessions.db
sqlite3> SELECT * FROM sessions;

# Inspect logs
sqlite3 ~/.homestead/watchtower.db
sqlite3> SELECT * FROM logs ORDER BY timestamp DESC LIMIT 10;

# Inspect tasks
sqlite3 ~/.homestead/steward/tasks.db
sqlite3> SELECT * FROM tasks WHERE status='open';
```

---

## Common Development Tasks

### Adding a New Package

1. Create package directory:
   ```bash
   mkdir -p packages/new-package/new_package
   ```

2. Create `pyproject.toml`:
   ```toml
   [project]
   name = "new-package"
   version = "0.1.0"
   description = "Description"
   requires-python = ">=3.11"
   dependencies = [
       "homestead-common",  # If needed
   ]

   [project.scripts]
   new-package = "new_package.main:main"
   ```

3. Create package structure:
   ```bash
   touch packages/new-package/new_package/__init__.py
   touch packages/new-package/new_package/main.py
   ```

4. Install in development mode:
   ```bash
   pip install -e packages/new-package
   ```

### Adding a New Manor Page

1. Create page directory:
   ```bash
   mkdir manor/src/app/new-page
   ```

2. Create `page.tsx`:
   ```typescript
   export default function NewPage() {
     return (
       <div>
         <h1>New Page</h1>
       </div>
     );
   }
   ```

3. Add API router if needed:
   ```python
   # manor/api/routers/new_router.py
   from fastapi import APIRouter

   router = APIRouter(prefix="/new", tags=["new"])

   @router.get("/")
   def get_data():
       return {"message": "Hello from new router"}
   ```

4. Register router in `manor/api/main.py`:
   ```python
   from .routers import new_router

   app.include_router(new_router.router)
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run specific package tests
pytest packages/herald/tests/

# Run with coverage
pytest --cov=packages --cov-report=html
```

---

## Code Style

### Python

- Follow PEP 8
- Use type hints where practical
- Document functions with docstrings
- Use `black` for formatting (optional)

```bash
# Format code
black packages/herald/herald/

# Check style
flake8 packages/herald/herald/
```

### TypeScript

- Follow the existing ESLint configuration
- Use TypeScript strict mode
- Prefer functional components with hooks

```bash
# Lint frontend code
cd manor
npm run lint

# Fix auto-fixable issues
npm run lint -- --fix
```

---

## Repository Structure

```
homestead/
├── docs/                     # Documentation
│   ├── user-guide/          # User guides
│   ├── dev-guide/           # Developer guides
│   ├── reference/           # API reference
│   ├── architecture/        # Architecture docs
│   └── roadmaps/            # Planning docs
├── lore/                     # AI identity files
│   ├── soul.md              # Core identity
│   ├── claude.md            # Behavior directives
│   ├── user.md              # User context
│   └── templates/           # Template files
├── manor/                    # Web dashboard
│   ├── api/                 # FastAPI backend
│   └── src/                 # Next.js frontend
├── packages/                 # Python packages
│   ├── common/              # Shared infrastructure
│   ├── herald/              # Telegram bot
│   ├── steward/             # Task management
│   ├── almanac/             # Job scheduling
│   └── mcp-homestead/       # MCP server
├── .env                      # Environment config
├── .gitignore               # Git ignore patterns
├── README.md                # Project README
└── CONTRIBUTING.md          # Contribution guidelines
```

---

## Getting Help

- **Documentation:** See [START_HERE.md](../START_HERE.md)
- **Architecture:** Read [Architecture Overview](../architecture/overview.md)
- **Issues:** Check existing issues or create a new one
- **Code:** Read the source code - it's documented!

---

**Last Updated:** 2026-01-31
