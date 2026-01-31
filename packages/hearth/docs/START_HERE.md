# 🔥 START HERE - Get Hearth Running

## Prerequisites Check

Before starting, you need:

1. **Python 3.10+** ✅ (you have 3.12)
2. **Virtual environment** ✅ (exists at `/opt/hearth/venv`)
3. **API Key** (at least one):
   - XAI (Grok) - recommended, fast and cheap
   - Anthropic (Claude) - if you have API key
   - OpenAI (GPT) - optional
   - Google (Gemini) - optional

---

## Step 1: Set Environment Variables

```bash
# Edit your shell config
nano ~/.bashrc  # or ~/.zshrc if using zsh

# Add these lines:
export ENTITY_HOME="$HOME/.hearth"
export ENTITY_USER="$USER"

# Add at least ONE API key:
export XAI_API_KEY="your_xai_key_here"           # Recommended
# export ANTHROPIC_API_KEY="your_anthropic_key"  # Or this
# export OPENAI_API_KEY="your_openai_key"        # Or this
# export GOOGLE_API_KEY="your_google_key"        # Or this

# Save and reload
source ~/.bashrc
```

**Verify:**
```bash
echo $ENTITY_HOME  # Should show /home/yourusername/.hearth
echo $XAI_API_KEY  # Should show your key
```

---

## Step 2: Create Entity Home

```bash
mkdir -p ~/.hearth/{data,reflections,skills,projects,pending}
```

**Verify:**
```bash
ls ~/.hearth
# Should show: data  pending  projects  reflections  skills
```

---

## Step 3: Install Missing Dependencies (Optional)

```bash
cd /opt/hearth
source venv/bin/activate

# Install optional providers (if you want them)
pip install openai google-generativeai
```

**Test imports:**
```bash
python -c "from core import get_config; print('✅ Core works')"
```

---

## Step 4: Start Hearth

### Quick Test (Manual)

```bash
hearth serve
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
```

**Test it:**
- Open http://localhost:8420/ in browser
- You should see the chat interface
- Type a message and press Enter
- The entity should respond

Press **Ctrl+C** to stop when done testing.

### Production Install (Recommended)

```bash
# Install as systemd service
sudo /opt/hearth/install-service.sh

# Start it
sudo systemctl start hearth

# Check it's running
sudo systemctl status hearth

# View logs
sudo journalctl -u hearth -f
```

**Test it:**
- Open http://localhost:8420/
- Service runs automatically on boot
- Restarts if it crashes

---

## Step 5: First Interaction

### Via Web UI (Easiest)

1. Go to http://localhost:8420/
2. Type: "Hello! What can you do?"
3. Press Enter
4. Watch the entity respond

### Via CLI

```bash
# Quick status
hearth status

# Single question
hearth ask "What is your purpose?"

# Interactive chat
hearth chat
```

### Via REST API

```bash
# Health check
curl http://localhost:8420/api/health

# Create a task
curl -X POST http://localhost:8420/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Test task", "priority": 1}'
```

---

## What to Do Next

### 1. Give it a Name

```bash
hearth name
```

The entity will propose names. Then:
```bash
hearth setname "YourChosenName"
```

### 2. Explore the Web UI

Visit http://localhost:8420/ and check out:
- **Chat** (/) - Talk to the entity
- **Tasks** (/tasks) - Manage work queue
- **Skills** (/skills) - Teach it capabilities
- **Projects** (/projects) - Track multi-day work
- **Proposals** (/proposals) - Review self-improvements
- **Status** (/status) - System overview
- **Reflections** (/reflections) - Past reflections
- **Debug** (/debug) - System introspection
- **Config** (/config) - Settings

### 3. Create Your First Task

Web UI: http://localhost:8420/tasks → "Create Task"

Or via CLI:
```bash
curl -X POST http://localhost:8420/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Research quantum computing basics",
    "description": "Summarize key concepts and applications",
    "priority": 2
  }'
```

### 4. Teach it a Skill

Web UI: http://localhost:8420/skills → "Create Skill"

Or via CLI:
```bash
curl -X POST http://localhost:8420/api/skills \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Git Workflow",
    "description": "Common git commands and patterns",
    "content": "# Git Basics\n\n```bash\ngit status\ngit add .\ngit commit -m \"message\"\ngit push\n```",
    "tags": ["git", "development"]
  }'
```

### 5. Let it Work Autonomously

The entity will:
- Process tasks in its queue during nightshift
- Reflect every 4 hours
- Propose self-improvements
- Learn from experiences
- Build continuity

Just leave it running!

---

## Troubleshooting

### "Connection refused" when accessing Web UI

```bash
# Check if service is running
sudo systemctl status hearth

# Or if running manually
ps aux | grep hearth

# Check the port
curl http://localhost:8420/api/health
```

### "No API key found" error

```bash
# Verify environment variable is set
echo $XAI_API_KEY

# If running as service, add to service file:
sudo nano /etc/systemd/system/hearth.service

# Add under [Service]:
Environment="XAI_API_KEY=your_key_here"

# Then reload:
sudo systemctl daemon-reload
sudo systemctl restart hearth
```

### Database permission errors

```bash
# Make sure entity home is writable
ls -la ~/.hearth

# Fix permissions if needed
chmod -R u+w ~/.hearth
```

### Service won't start

```bash
# Check logs
sudo journalctl -u hearth -n 50 --no-pager

# Common issues:
# - Port 8420 already in use: sudo lsof -i :8420
# - Missing API key: Check service file
# - Permission errors: Check User/Group in service file
```

---

## Quick Reference

### Start/Stop
```bash
# Manual
hearth serve              # Start (Ctrl+C to stop)

# Service
sudo systemctl start hearth
sudo systemctl stop hearth
sudo systemctl restart hearth
```

### Status
```bash
hearth status             # Quick status
sudo systemctl status hearth  # Service status
curl http://localhost:8420/api/health  # API health
```

### Logs
```bash
sudo journalctl -u hearth -f     # Follow logs
sudo journalctl -u hearth -n 100  # Last 100 lines
```

### Web Access
```bash
# Web UI
http://localhost:8420/

# REST API
http://localhost:8420/api/

# API Docs
http://localhost:8420/api/docs
```

---

## Ready to Go!

Once you complete steps 1-4, you have:

✅ A running AI entity
✅ Web interface
✅ REST API
✅ Autonomous agent
✅ Self-improvement system

**Now start building!** 🚀

The entity will learn, grow, and evolve as you use it.

---

## Need Help?

- Check **[QUICKSTART.md](QUICKSTART.md)** for detailed guide
- Read **[SERVICE_SETUP.md](SERVICE_SETUP.md)** for service management
- See **[UNIFIED_SERVICE.md](UNIFIED_SERVICE.md)** for architecture
- Review **[V1_ULTIMATE.md](V1_ULTIMATE.md)** for full capabilities

---

*Hearth v1.0+ - Your AI entity infrastructure* 🔥
