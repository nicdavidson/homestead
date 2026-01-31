#!/bin/bash
# Clean up Hearth directory structure and initialize git repo

set -e

echo "========================================================================"
echo "🔥 Hearth - Git Repository Setup & Cleanup"
echo "========================================================================"
echo ""

# 1. Create directory structure
echo "Creating directory structure..."
mkdir -p .dev/{docs,tests,scripts,logs}
mkdir -p docs

# 2. Move development/planning documents to .dev/docs
echo "Moving planning documents..."
mv -f GOOD_MORNING*.md .dev/docs/ 2>/dev/null || true
mv -f V1_*.md .dev/docs/ 2>/dev/null || true
mv -f BUILD_STATUS.md .dev/docs/ 2>/dev/null || true
mv -f CHAT_AGENT_FIX.md .dev/docs/ 2>/dev/null || true
mv -f CLI_REFACTORING_COMPLETE.md .dev/docs/ 2>/dev/null || true
mv -f IMPLEMENTATION_STATUS.md .dev/docs/ 2>/dev/null || true
mv -f REFACTORING_SUMMARY.md .dev/docs/ 2>/dev/null || true
mv -f TEST_RESULTS*.md .dev/docs/ 2>/dev/null || true
mv -f TEST_RESULTS*.txt .dev/docs/ 2>/dev/null || true
mv -f WEB_UI_UPGRADE.md .dev/docs/ 2>/dev/null || true
mv -f NO_SUDO_SETUP.txt .dev/docs/ 2>/dev/null || true

# 3. Move test scripts to .dev/tests
echo "Moving test scripts..."
mv -f test_*.py .dev/tests/ 2>/dev/null || true

# 4. Move utility scripts to .dev/scripts
echo "Moving utility scripts..."
mv -f run.sh .dev/scripts/ 2>/dev/null || true
mv -f show-results.sh .dev/scripts/ 2>/dev/null || true

# 5. Move logs to .dev/logs
echo "Moving logs..."
mv -f log.txt .dev/logs/ 2>/dev/null || true
mv -f *.log .dev/logs/ 2>/dev/null || true

# 6. Move user-facing documentation to docs/
echo "Organizing documentation..."
mv -f QUICKSTART.md docs/ 2>/dev/null || true
mv -f START_HERE.md docs/ 2>/dev/null || true
mv -f SERVICE_SETUP.md docs/ 2>/dev/null || true
mv -f UNIFIED_SERVICE.md docs/ 2>/dev/null || true
mv -f ARCHITECTURE.md docs/ 2>/dev/null || true

# 7. Remove old/superseded files
echo "Removing old files..."
rm -f cli.py hearth.py __init__.py 2>/dev/null || true

# 8. Create .gitignore
echo "Creating .gitignore..."
cat > .gitignore << 'EOF'
# Development & Testing (keep locally, don't commit)
.dev/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
dist/
build/
*.egg

# Virtual Environment
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Logs
*.log

# Environment variables (sensitive)
.env
*.key

# Database (entity-specific data)
*.db
*.db-journal

# Temporary files
*.tmp
*.temp
.cache/

# User data (each entity has their own)
data/
reflections/
skills/
projects/
pending/

# Test outputs
.pytest_cache/
.coverage
htmlcov/

# OS
Thumbs.db
EOF

# 9. Create clean README.md
echo "Creating README.md..."
cat > README.md << 'EOF'
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

```bash
# 1. Set environment
export ENTITY_HOME="$HOME/.hearth"
export ENTITY_USER="$USER"
export XAI_API_KEY="your_key_here"

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the service
python main.py serve

# 4. Open Web UI
open http://localhost:8420/
```

**Or install as systemd service:**

```bash
sudo ./install-service.sh
sudo systemctl start hearth
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
```

## Requirements

- Python 3.10+
- At least one API key (XAI, Anthropic, OpenAI, or Google)
- Linux/macOS (Windows via WSL)

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
├── main.py            # CLI entry point
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
ENTITY_HOME=/tmp/test_entity python main.py serve
```

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
EOF

# 10. Initialize git repository
echo ""
echo "Initializing git repository..."
git init
git add .
git commit -m "Initial commit - Hearth v1.0+

- Unified service architecture (Nightshift + API + Web UI)
- Multi-provider support (XAI, Claude, OpenAI, Gemini)
- Complete Web UI with HTMX
- REST API with 18 endpoints
- Task, skill, and project management
- Self-improvement proposal system
- Production-ready systemd service"

# 11. Summary
echo ""
echo "========================================================================"
echo "✅ Git repository initialized!"
echo "========================================================================"
echo ""
echo "Structure:"
echo "  /opt/hearth/"
echo "  ├── .dev/          # Development files (not in git)"
echo "  │   ├── docs/      # Planning documents"
echo "  │   ├── tests/     # Test scripts"
echo "  │   ├── scripts/   # Utility scripts"
echo "  │   └── logs/      # Log files"
echo "  ├── docs/          # User documentation (in git)"
echo "  ├── core/          # Core systems"
echo "  ├── agents/        # Agent implementations"
echo "  ├── web/           # Web UI"
echo "  └── ..."
echo ""
echo "Git status:"
git status
echo ""
echo "Next steps:"
echo "  1. Review: git log"
echo "  2. Add remote: git remote add origin <url>"
echo "  3. Push: git push -u origin master"
echo ""
echo "Development files preserved in .dev/ (not tracked by git)"
echo "========================================================================"
EOF
