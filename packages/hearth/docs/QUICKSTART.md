# Hearth Quick Start Guide

## Step 1: Verify Installation

Run the verification script to check everything is ready:

```bash
/opt/hearth/venv/bin/python /opt/hearth/verify-install.py
```

This checks:
- ✅ Python version (3.10+)
- ✅ Virtual environment
- ✅ Required packages
- ✅ Entity home directory
- ✅ API keys configured
- ✅ Core modules work
- ✅ Database initializes

If any checks fail, it tells you how to fix them.

---

## Step 2: Configure Environment

### Set Environment Variables

```bash
# Add to ~/.bashrc or ~/.zshrc
export ENTITY_HOME="$HOME/.hearth"
export ENTITY_USER="$USER"

# At least one API key (choose what you have)
export XAI_API_KEY="your_xai_key_here"           # For Grok
export ANTHROPIC_API_KEY="your_anthropic_key"    # For Claude
export OPENAI_API_KEY="your_openai_key"          # For GPT
export GOOGLE_API_KEY="your_google_key"          # For Gemini

# Reload shell
source ~/.bashrc  # or source ~/.zshrc
```

### Create Entity Home

```bash
mkdir -p ~/.hearth/{data,reflections,skills,projects,pending}
```

---

## Step 3: Run Quick Tests

Test core functionality:

```bash
cd /opt/hearth

# Test with test entity (safe)
ENTITY_HOME=/home/test_entity ENTITY_USER=test_entity \
  venv/bin/python -m pytest tests/ -v

# Or run individual test suites
ENTITY_HOME=/home/test_entity ENTITY_USER=test_entity \
  venv/bin/python /tmp/claude/.../scratchpad/test_v1_ultimate.py
```

Expected result: All tests pass ✅

---

## Step 4: Start the Entity

### Option A: Manual Start (Testing)

```bash
# Start unified service (everything)
hearth serve

# Or specify port
hearth serve --host 0.0.0.0 --port 8420
```

You should see:
```
======================================================================
🔥 Hearth Unified Service
======================================================================

📡 Web UI:     http://0.0.0.0:8420/
🔌 REST API:  http://0.0.0.0:8420/api/
📚 API Docs:  http://0.0.0.0:8420/api/docs
🌙 Nightshift: Running in background

======================================================================
```

**Test it:**
- Open http://localhost:8420/ in browser
- Check Web UI loads
- Navigate through pages (Tasks, Skills, Projects, etc.)
- Try creating a task

Press Ctrl+C to stop.

### Option B: Production Service (Recommended)

```bash
# Install systemd service
sudo /opt/hearth/install-service.sh

# Start it
sudo systemctl start hearth

# Check status
sudo systemctl status hearth

# View logs
sudo journalctl -u hearth -f
```

**Test it:**
- Open http://localhost:8420/ in browser
- Service runs automatically on boot
- Restarts on failure

---

## Step 5: First Interaction

### Via Web UI

1. Open http://localhost:8420/
2. Type a message in the chat
3. Submit
4. Watch the entity respond

### Via CLI

```bash
# Quick status check
hearth status

# Interactive chat
hearth chat

# Single question
hearth ask "What can you do?"

# Trigger reflection
hearth reflect
```

### Via REST API

```bash
# Health check
curl http://localhost:8420/api/health

# Create a task
curl -X POST http://localhost:8420/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "My first task", "priority": 2}'

# List tasks
curl http://localhost:8420/api/tasks

# Create a skill
curl -X POST http://localhost:8420/api/skills \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Python Best Practices",
    "description": "Common Python patterns",
    "content": "# Best Practices\n\n1. Use type hints\n2. Write docstrings",
    "tags": ["python", "coding"]
  }'

# Search skills
curl http://localhost:8420/api/skills/search?query=python
```

---

## What to Try Next

### 1. Give it a Name

```bash
# Trigger naming ceremony
hearth name

# Or set directly
hearth setname "YourChosenName"
```

The entity will propose names based on its personality.

### 2. Create Some Tasks

Via Web UI or CLI:
```bash
# Create task via API
curl -X POST http://localhost:8420/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Learn about quantum computing",
    "description": "Research and summarize key concepts",
    "priority": 2
  }'
```

The entity will process these during nightshift.

### 3. Teach it Skills

Via Web UI (`/skills`) or:
```bash
# Create a skill
curl -X POST http://localhost:8420/api/skills \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Docker Commands",
    "description": "Common Docker operations",
    "content": "# Docker Basics\n\n```bash\ndocker ps\ndocker build -t name .\ndocker run -d -p 8080:80 name\n```",
    "tags": ["docker", "devops"]
  }'
```

### 4. Start a Project

Via Web UI (`/projects`) or:
```bash
# Create project
curl -X POST http://localhost:8420/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Build Personal Website",
    "description": "Create portfolio site with blog",
    "goals": [
      "Design wireframes",
      "Set up Next.js",
      "Implement blog",
      "Deploy to Vercel"
    ]
  }'
```

### 5. Let it Reflect

Reflections happen automatically every 4 hours during nightshift, or trigger manually:

```bash
hearth reflect
```

View reflections at http://localhost:8420/reflections

### 6. Review Proposals

The entity will propose self-improvements. Review them at:
- Web UI: http://localhost:8420/proposals
- Or via API: `curl http://localhost:8420/api/proposals`

Approve good ones to let the entity improve itself.

---

## Monitoring

### Check Status

```bash
# Via CLI
hearth status

# Via API
curl http://localhost:8420/api/status

# Via Web UI
open http://localhost:8420/status
```

### View Logs

```bash
# If running as service
sudo journalctl -u hearth -f

# If running manually
# Logs appear in terminal
```

### Debug Information

Web UI: http://localhost:8420/debug

Shows:
- System configuration
- Recent tasks
- Active subagents
- Provider status

---

## Common Commands

```bash
# Start/stop service
sudo systemctl start hearth
sudo systemctl stop hearth
sudo systemctl restart hearth

# View status
hearth status
sudo systemctl status hearth

# View logs
sudo journalctl -u hearth -f

# Interactive chat
hearth chat

# Quick question
hearth ask "question here"

# Trigger reflection
hearth reflect

# Show costs
hearth costs

# Show identity
hearth identity
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u hearth -n 50

# Verify installation
/opt/hearth/venv/bin/python /opt/hearth/verify-install.py

# Check port availability
sudo lsof -i :8420
```

### Can't Access Web UI

```bash
# Check if service is running
sudo systemctl status hearth

# Try accessing locally first
curl http://localhost:8420/api/health

# Check firewall
sudo ufw allow 8420/tcp
```

### API Keys Not Working

```bash
# Verify keys are set
echo $XAI_API_KEY
echo $ANTHROPIC_API_KEY

# Add to service file if running as service
sudo nano /etc/systemd/system/hearth.service
# Add: Environment="XAI_API_KEY=your_key"

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart hearth
```

### Database Errors

```bash
# Check entity home exists
ls -la $ENTITY_HOME

# Reinitialize if needed
rm -f $ENTITY_HOME/data/hearth.db
hearth serve  # Will recreate on start
```

---

## Summary: Getting Started

**Quick version:**

```bash
# 1. Verify
/opt/hearth/venv/bin/python /opt/hearth/verify-install.py

# 2. Set environment (add to ~/.bashrc)
export ENTITY_HOME="$HOME/.hearth"
export ENTITY_USER="$USER"
export XAI_API_KEY="your_key"

# 3. Start it
hearth serve

# Or install as service
sudo /opt/hearth/install-service.sh
sudo systemctl start hearth

# 4. Use it
open http://localhost:8420/
```

That's it! 🔥

---

## Next Steps

Once running:
1. Give it a name: `hearth name`
2. Create some tasks
3. Teach it skills
4. Start a project
5. Let it work autonomously
6. Review its reflections and proposals

The entity will learn, improve, and evolve over time.

---

*Hearth v1.0+ - Ready for Production* 🚀
