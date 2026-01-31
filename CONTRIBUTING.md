# Contributing to Homestead

Thank you for your interest in contributing to Homestead. This guide covers everything you need to get started, from initial setup through opening a pull request.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Workflow](#development-workflow)
3. [Project Structure](#project-structure)
4. [Adding a New Package](#adding-a-new-package)
5. [The Homestead Naming Convention](#the-homestead-naming-convention)
6. [Code Style](#code-style)
7. [Testing](#testing)
8. [Architecture Notes](#architecture-notes)

---

## Getting Started

### Prerequisites

- **Python 3.11+** (3.12 recommended)
- **Node.js 20+** and npm (for the Manor web dashboard)
- **SQLite 3** (bundled with Python, but the `sqlite3` CLI is useful for debugging)
- **ruff** for linting and formatting (`pip install ruff`)
- **pytest** for running tests (`pip install pytest`)

### Fork and Clone

```bash
# Fork on GitHub, then:
git clone https://github.com/<your-username>/homestead.git
cd homestead
```

### Initial Setup

Run the setup script, which creates data directories, copies `.env.example` files, creates a Python virtual environment, and installs dependencies:

```bash
bash setup.sh
```

Or do it manually:

```bash
# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install all Python packages in editable mode
pip install -e packages/common
pip install -e packages/herald
pip install -e packages/steward
pip install -e packages/almanac

# Install development tools
pip install ruff pytest

# Create the data directory
mkdir -p ~/.homestead/{scratchpad,skills,steward,almanac}

# Copy environment files
cp .env.example .env
cp packages/herald/.env.example packages/herald/.env
# Edit .env files with your values
```

### Running Services Locally

```bash
# Herald (Telegram bot)
make herald

# Manor API backend (port 8700)
make manor-api

# Manor frontend (port 3000)
cd manor && npm install && npm run dev

# Almanac scheduler
make almanac

# Run all three main services in parallel
make -j3 herald manor-api manor-ui
```

---

## Development Workflow

### Branch Naming

Use descriptive branch names with a category prefix:

| Prefix | Use |
|---|---|
| `feat/` | New features or packages |
| `fix/` | Bug fixes |
| `refactor/` | Code restructuring without behavior changes |
| `docs/` | Documentation only |
| `test/` | Adding or improving tests |
| `chore/` | Dependency updates, CI changes, tooling |

Examples:
- `feat/herald-image-support`
- `fix/outbox-polling-race`
- `refactor/watchtower-async`
- `docs/api-reference`

### Commits

Write clear, imperative commit messages. Keep the subject line under 72 characters. Use the body for context when needed.

```
Add outbox retry logic for failed messages

Previously, failed outbox messages were marked as 'failed' permanently.
Now they are retried up to 3 times with exponential backoff before being
marked as permanently failed.
```

Avoid vague messages like "fix stuff" or "update code."

### Pull Requests

1. Create a branch from `main`.
2. Make your changes. Ensure `make lint` and `make test` pass.
3. Push your branch and open a PR against `main`.
4. Describe what the PR does and why. Reference any relevant issues.
5. PRs that touch Python code must pass the `lint` and `test` CI jobs.
6. PRs that touch the Manor frontend must pass `manor-lint` and `manor-build`.

### CI Pipeline

The GitHub Actions CI runs automatically on pushes and PRs to `main`:

| Job | What it checks |
|---|---|
| `lint` | `ruff check` and `ruff format --check` on all Python code |
| `test` | `pytest` on the `tests/` directory |
| `manor-lint` | TypeScript type checking and ESLint |
| `manor-build` | Next.js production build |

---

## Project Structure

```
homestead/
  .github/workflows/       CI configuration
  docs/                    Architecture and API documentation
  docker/                  Dockerfiles for each service
  lore/                    AI identity and persona files (markdown)
  manor/                   Web dashboard
    api/                   FastAPI backend (Python)
      routers/             API route handlers
      config.py            Settings from environment
      main.py              App entrypoint
    src/                   Next.js frontend (TypeScript)
  packages/
    common/                Shared infrastructure
      common/
        watchtower.py      Structured SQLite logging
        outbox.py          Cross-package message delivery
        skills.py          Skill file management
        models.py          Agent identities and data models
        db.py              SQLite connection utilities
    herald/                Telegram bot (aiogram)
      herald/
        bot.py             Bot handlers, middleware, queue processor
        claude.py          Claude CLI process spawning and stream parsing
        providers.py       Model provider routing (Claude CLI, Grok API)
        sessions.py        Session management (SQLite)
        prompt.py          System prompt assembly from lore/skills
        queue.py           Per-chat message queue
        auth.py            Telegram user authorization
        config.py          Herald-specific settings
        main.py            Entrypoint
    steward/               Task management
      steward/
        models.py          Task, Blocker, Priority data models
        store.py           SQLite task CRUD
        main.py            Entrypoint
    almanac/               Job scheduling
      almanac/
        models.py          Job, Schedule, Action data models
        store.py           SQLite job CRUD with cron parsing
        scheduler.py       Async scheduler loop
        main.py            Entrypoint
    hearth/                AI personality and agent framework
      agents/              Agent definitions (opus, sonnet, grok, etc.)
      core/                Skills, sessions, routing, config, providers
      integrations/        Telegram and CLI integration hooks
      web/                 Web interface components
  scripts/                 Utility scripts
  tests/                   Test suite (pytest)
  docker-compose.yml       Multi-service Docker orchestration
  Makefile                 Common development commands
  pyproject.toml           Root project config (ruff, pytest)
  setup.sh                 First-time setup script
```

---

## Adding a New Package

Homestead is organized as a monorepo of Python packages under `packages/`. Each package is independently installable via `pip install -e`.

### Step-by-Step

1. **Create the directory structure:**

```bash
mkdir -p packages/your-package/your_package
touch packages/your-package/your_package/__init__.py
touch packages/your-package/your_package/main.py
```

2. **Create `pyproject.toml`:**

```toml
[project]
name = "your-package"
version = "0.1.0"
description = "Brief description of what this package does"
requires-python = ">=3.11"
dependencies = []

[project.scripts]
your-package = "your_package.main:main"

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"
```

3. **Install in development mode:**

```bash
pip install -e packages/your-package
```

4. **Integrate with common infrastructure (optional but encouraged):**

```python
# Use Watchtower for structured logging
from common.watchtower import Watchtower, WatchtowerHandler
wt = Watchtower()
handler = WatchtowerHandler(wt, source="your-package")
logging.getLogger().addHandler(handler)

# Use the outbox to send messages through Telegram
from common.outbox import post_message
post_message(
    db_path="~/.homestead/outbox.db",
    chat_id=12345,
    agent_name="your-package",
    message="Hello from your package!",
)
```

5. **If your package stores state, use SQLite:**
   - Store the database under `~/.homestead/your-package/`.
   - Use WAL mode and a 5000ms busy timeout (see `common.db.get_connection`).

6. **Add your package to the test PYTHONPATH** in the Makefile `test` target if it has tests.

7. **Register the agent identity** in `common/common/models.py` if the package sends messages through the outbox.

### Package Naming

All packages must follow the homestead naming convention (see below). Choose a name that evokes a part of a homestead or rural property.

---

## The Homestead Naming Convention

Every package in the project is named after a part of a homestead -- a self-sufficient home. This is a core identity of the project, not a suggestion. The metaphor creates a cohesive, memorable system where each component's name hints at its role.

### Current Names and Their Roles

| Package | Metaphor | Role |
|---|---|---|
| **common** | Shared grounds | Shared infrastructure (logging, messaging, skills, models) |
| **herald** | The town crier | Telegram bot interface -- delivers messages to and from the outside world |
| **steward** | The estate manager | Task management -- tracks work, priorities, blockers |
| **almanac** | The farmer's almanac | Job scheduling -- knows when things need to happen |
| **hearth** | The fireplace | AI personality layer -- the warm center of the home |
| **manor** | The main house | Web dashboard -- the grand interface to the whole estate |
| **watchtower** | The lookout post | Structured logging -- observes everything that happens (part of common) |
| **outbox** | The mailbox | Cross-package messaging -- letters waiting to be delivered (part of common) |
| **lore** | The family history | AI identity files -- the estate's traditions and values |

### Guidelines for New Names

- The name should be a **single English word** (or a well-known compound) that evokes a structure, role, or feature of a rural homestead.
- The name should be **suggestive of the package's function**. Someone reading the name should get a rough idea of what it does.
- Avoid generic tech terms. "service" or "handler" would violate the convention. "Forge" (for a build system) or "Cellar" (for archival storage) would follow it.
- Some names that are still available and might suit future packages: forge, cellar, stable, orchard, well, fence, gate, barn, pasture, thicket, root-cellar, workshop, mill, silo, grove.

---

## Code Style

### Linting and Formatting

All Python code is linted and formatted with [ruff](https://docs.astral.sh/ruff/).

```bash
# Check for issues
make lint

# Auto-fix what can be fixed
make lint-fix

# Format code
make format
```

The ruff configuration is in the root `pyproject.toml`:

```toml
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I"]
```

This enables pyflakes (`F`), pycodestyle errors and warnings (`E`, `W`), and isort-compatible import sorting (`I`). Line length is 100 characters.

### Type Hints

Use type hints on all function signatures. The codebase uses modern Python typing throughout:

```python
from __future__ import annotations

def query(
    self,
    since: float | None = None,
    level: str | None = None,
    limit: int = 100,
) -> list[LogEntry]:
    ...
```

Key conventions:
- Always include `from __future__ import annotations` at the top of every module.
- Use `X | None` instead of `Optional[X]`.
- Use `list[X]`, `dict[X, Y]` lowercase generics (not `List`, `Dict`).
- Use `str | Path` for path parameters that accept both.
- Annotate return types, even for `-> None`.

### Async Patterns

Herald, Almanac, and the Manor chat WebSocket all use `asyncio`. Follow these conventions:

- Use `async def` for I/O-bound operations (network calls, subprocess spawning).
- Use `asyncio.create_task()` for fire-and-forget background work (e.g., outbox polling, typing indicators).
- Use `asyncio.wait_for()` with explicit timeouts for external processes.
- Always handle `asyncio.CancelledError` gracefully -- clean up resources before re-raising.
- For blocking operations inside async code, use `loop.run_in_executor()`.

```python
# Good: explicit timeout
try:
    await asyncio.wait_for(proc.communicate(), timeout=60)
except asyncio.TimeoutError:
    proc.kill()
    await proc.wait()
```

### SQLite Conventions

Every package that stores state uses SQLite with consistent settings:

```python
conn = sqlite3.connect(str(db_path))
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=5000")
conn.row_factory = sqlite3.Row
```

- Always use WAL mode for concurrent read access.
- Always set `busy_timeout=5000` to handle lock contention gracefully.
- Always use `sqlite3.Row` as the row factory for dict-like access.
- Always use parameterized queries (`?` placeholders) -- never string interpolation.
- Create tables with `CREATE TABLE IF NOT EXISTS` for idempotent initialization.

### General Principles

- **No external database servers.** SQLite for persistence, filesystem for content.
- **Environment variables for configuration.** Loaded via `python-dotenv`.
- **Self-contained routers.** Manor API routers duplicate schema definitions rather than importing from package code, keeping the API decoupled from the Python packages.
- **Anti-sycophancy by design.** The AI identity is opinionated and direct. Contributions to lore or prompt engineering should maintain this tone.

---

## Testing

### Running Tests

```bash
# Run the full test suite
make test

# Run tests for just the common package
make test-common

# Run a specific test file
PYTHONPATH=packages/common:packages/herald:packages/steward:packages/almanac \
  pytest tests/test_watchtower.py -v

# Run a specific test
PYTHONPATH=packages/common:packages/herald:packages/steward:packages/almanac \
  pytest tests/test_outbox.py::test_post_and_retrieve -v
```

### Test Configuration

Tests use pytest with async support via `asyncio_mode = "auto"` (configured in root `pyproject.toml`). The test paths are set to `tests/`.

### Where to Add Tests

All tests live in the top-level `tests/` directory. The naming convention mirrors the module being tested:

| Module | Test file |
|---|---|
| `common.watchtower` | `tests/test_watchtower.py` |
| `common.outbox` | `tests/test_outbox.py` |
| `common.models` | `tests/test_models.py` |
| `common.skills` | `tests/test_skills.py` |
| `common.db` | `tests/test_db.py` |

When adding a new module, create a corresponding `tests/test_<module>.py` file. If you add a new package, add its path to the `PYTHONPATH` in the Makefile `test` target.

### Writing Tests

- Use `tmp_path` (pytest fixture) for any test that creates files or databases. Never write to real data directories.
- Use `conftest.py` for shared fixtures.
- Test the public API of each module, not internal implementation details.
- For async code, just write `async def test_something():` -- the `asyncio_mode = "auto"` setting handles the event loop.

```python
def test_watchtower_logs_and_queries(tmp_path):
    """Watchtower should persist logs and return them via query."""
    db_path = tmp_path / "watchtower.db"
    wt = Watchtower(db_path)
    wt.log("INFO", "test", "hello world")

    results = wt.query(limit=10)
    assert len(results) == 1
    assert results[0].message == "hello world"
```

---

## Architecture Notes

For a deeper understanding of how the system fits together, see:

- **[Architecture Document](docs/architecture.md)** -- system overview, data flow, database schemas, package dependencies.
- **[API Reference](docs/api-reference.md)** -- complete Manor REST and WebSocket endpoint documentation.
- **[README](README.md)** -- quickstart, configuration reference, and customization guide.
