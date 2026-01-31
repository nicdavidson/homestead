# 🔥 Hearth

**AI Entity Infrastructure**

A production-ready framework for autonomous AI entities with memory, self-improvement, and continuous operation.

## Features

- 🌙 **Nightshift Daemon** - Autonomous background worker
- 🌐 **Web UI** - Complete human interface (HTMX)
- 🔌 **REST API** - 18 endpoints for programmatic access
- 🧠 **Memory Systems** - Tasks, skills, projects, reflections
- 🔄 **Self-Improvement** - Proposes and implements code changes
- 🤖 **Multi-Provider** - XAI Grok, Claude, OpenAI, Gemini
- 📊 **Cost Tracking** - Monitor API usage and budgets
- 🔐 **Identity System** - Named entities with continuity

## Quick Start

### With sudo (Separate Entity User)

```bash
# 1. Run automated setup
./setup.sh

# 2. Start service
sudo systemctl start hearth
sudo systemctl enable hearth

# 3. Interact with entity (Web UI or CLI)
open http://localhost:8420/
# or: python main.py chat

# 4. After entity names itself
hearth apply-name          # Applies name to system user and hostname
sudo reboot                # Reboot for hostname to take effect
```

### Without sudo (User Home Directory)

```bash
# 1. Set environment
export ENTITY_HOME="$HOME/.hearth"
export ENTITY_USER="$USER"
export XAI_API_KEY="your_key_here"

# 2. Install dependencies
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Create entity home
mkdir -p ~/.hearth/identity

# 4. Start service
python main.py serve

# Or install as user service (runs on login)
systemctl --user enable hearth
systemctl --user start hearth
```

## Documentation

- **[docs/START_HERE.md](docs/START_HERE.md)** - Complete setup guide
- **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - Usage examples
- **[docs/SERVICE_SETUP.md](docs/SERVICE_SETUP.md)** - Production deployment
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design

## Architecture

```
hearth serve
├─ Nightshift (background thread)
│  └─ Autonomous task processing
└─ FastAPI Server (port 8420)
   ├─ /api/* → REST API (JSON)
   └─ /* → Web UI (HTML)
```

**Single process. Three services. Simple.**

## Commands

```bash
# Unified service (everything)
hearth serve

# Individual components
hearth daemon       # Just nightshift
hearth web          # Just web UI
python -m core.api  # Just REST API

# Utilities
hearth status       # System status
hearth chat         # Interactive chat
hearth reflect      # Trigger reflection
hearth name         # Naming ceremony
hearth setname NAME # Set entity name explicitly
hearth apply-name   # Apply entity's name to system user/hostname
```

## Entity Naming

Hearth entities name themselves through reflection and interaction:

1. **Setup** - Entity starts as user `_` (unnamed placeholder)
2. **First boot** - Entity interacts with you, reads soul.md and user.md
3. **Naming** - Entity chooses its own name based on identity and purpose
4. **Apply** - Run `hearth apply-name` to update system user and hostname
5. **Reboot** - Hostname change takes full effect

This gives entities agency in choosing their own identity.

## Setup Approaches

**Separate Entity User (Recommended):**
- Entity runs as dedicated system user (starts as `_`, later renamed)
- Home directory: `/home/_/` → `/home/milo/` (after naming)
- Runs 24/7 as systemd system service
- Independent of human user session
- Full process isolation
- **Requires:** sudo access

**User's Home Directory:**
- Entity runs as your user
- Home directory: `$HOME/.hearth`
- Can run as systemd user service (no sudo)
- Simpler permissions and setup
- Works in containers, cloud, shared hosting
- Good for single-user systems

**Both approaches are production-ready.** Choose based on your environment:
- **Have sudo?** → Separate user gives better isolation
- **No sudo?** → User home works great with user services

See [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) for detailed instructions.

## Requirements

- Python 3.10+
- At least one API key (XAI, Anthropic, OpenAI, or Google)
- Linux/macOS (Windows via WSL)
- sudo access (only for autonomous operation setup)

## Structure

```
/opt/hearth/
├── core/              # Core systems
│   ├── providers/     # AI model providers
│   ├── api.py         # REST API
│   ├── tasks.py       # Task management
│   ├── skills.py      # Skill system
│   └── ...
├── agents/            # Agent implementations
├── web/               # Web UI
│   ├── templates/     # HTML templates
│   └── static/        # CSS/JS
├── master.py            # CLI entry point
├── service.py         # Unified service
└── docs/              # Documentation
```

## API Access

**REST API:**
- Base: `http://localhost:8420/api/`
- Docs: `http://localhost:8420/api/docs`
- Health: `GET /api/health`

**Web UI:**
- Home: `http://localhost:8420/`
- Tasks: `http://localhost:8420/tasks`
- Skills: `http://localhost:8420/skills`
- Projects: `http://localhost:8420/projects`

## Development

```bash
# Activate venv
source venv/bin/activate

# Install dev dependencies
pip install -r requirements.txt

# Run verification
python verify-install.py

# Manual test
ENTITY_HOME=/tmp/test_entity python master.py serve
```

## Collaboration Model

Hearth uses a **distributed development model** where entities collectively improve the framework:

- Each user + entity pair works on a local fork/branch
- Entities propose improvements to their local instance
- Users review and merge locally
- Best improvements get contributed upstream via Pull Requests
- Everyone benefits from collective improvements

**Workflow:**
```bash
# 1. Fork and clone
git clone https://github.com/yourname/hearth.git /opt/hearth
git remote add upstream https://github.com/maintainer/hearth.git

# 2. Entity proposes improvement, you approve
# 3. Entity creates feature branch and implements
# 4. You test and merge to your branch

# 5. Contribute back to master repo
gh pr create --title "feat: your improvement"

# 6. Pull updates from upstream
git fetch upstream && git merge upstream/master
```

See **[docs/COLLABORATION_MODEL.md](docs/COLLABORATION_MODEL.md)** for complete workflow.

## Production Deployment

```bash
# Install as systemd service
sudo ./install-service.sh

# Manage service
sudo systemctl start hearth
sudo systemctl enable hearth
sudo systemctl status hearth

# View logs
sudo journalctl -u hearth -f
```

## License

MIT

## Status

**v1.0+ - Production Ready** ✅

- ✅ Core systems operational
- ✅ Multi-provider support
- ✅ Unified service architecture
- ✅ Complete test coverage
- ✅ Web UI + REST API
- ✅ Self-improvement system

Built with Claude Sonnet 4.5
