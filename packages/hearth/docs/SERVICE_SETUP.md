# Hearth Service Setup

## Overview

Hearth now runs as a **unified service** that combines all components in a single process:

- 🌙 **Nightshift Daemon** - Autonomous background worker (task queue, reflections, etc.)
- 🌐 **Web UI** - Human interface at `http://0.0.0.0:8420/`
- 🔌 **REST API** - Programmatic access at `http://0.0.0.0:8420/api/`

All three run together when you start the service.

---

## Quick Start

### Manual Run (Testing)

```bash
# Run unified service manually
hearth serve

# Or specify host/port
hearth serve --host 0.0.0.0 --port 8420

# Or run directly
python /opt/hearth/service.py
```

This starts everything. You'll see:
- Web UI at http://localhost:8420/
- REST API at http://localhost:8420/api/
- API docs at http://localhost:8420/api/docs
- Nightshift running in background

### Production (Systemd Service)

Install as a systemd service to run automatically on boot:

```bash
# Install the service
sudo /opt/hearth/install-service.sh

# Start it
sudo systemctl start hearth

# Check status
sudo systemctl status hearth

# View logs
sudo journalctl -u hearth -f
```

---

## Service Management

### Systemd Commands

```bash
# Start service
sudo systemctl start hearth

# Stop service
sudo systemctl stop hearth

# Restart service
sudo systemctl restart hearth

# Check status
sudo systemctl status hearth

# Enable auto-start on boot (already done by install script)
sudo systemctl enable hearth

# Disable auto-start
sudo systemctl disable hearth

# View logs (live tail)
sudo journalctl -u hearth -f

# View logs (last 100 lines)
sudo journalctl -u hearth -n 100

# View logs since boot
sudo journalctl -u hearth -b
```

### Manual Service Control

If you prefer not to use systemd:

```bash
# Run in foreground
hearth serve

# Run in background with nohup
nohup hearth serve > /var/log/hearth.log 2>&1 &

# Kill it
pkill -f "hearth serve"
```

---

## Architecture

### Unified Service (`service.py`)

The unified service combines all components:

```python
class HearthService:
    def run(self):
        # Start Nightshift in background thread
        self.start_nightshift()

        # Create unified FastAPI app
        # - /api/* -> REST API
        # - /* -> Web UI
        app = self.create_unified_app()

        # Run FastAPI server
        uvicorn.run(app, host="0.0.0.0", port=8420)
```

### Components

1. **Nightshift** (`agents/nightshift.py`)
   - Runs in background thread
   - Checks task queue every interval
   - Triggers reflections every 4 hours
   - Generates morning briefings
   - Non-blocking, daemon thread

2. **REST API** (`core/api.py`)
   - Mounted at `/api/`
   - 18 endpoints for programmatic access
   - OpenAPI docs at `/api/docs`
   - JSON responses

3. **Web UI** (`web/app.py`)
   - Mounted at `/`
   - HTMX-powered interface
   - Pages: Chat, Tasks, Skills, Projects, Proposals, Status, Debug, Config
   - Server-rendered HTML

### Process Tree

```
hearth serve (main process)
├─ Nightshift thread (background loop)
└─ Uvicorn FastAPI server
   ├─ /api/* -> REST API handlers
   └─ /* -> Web UI handlers
```

---

## Configuration

### Service File

Located at: `/opt/hearth/systemd/hearth.service`

Key settings:
```ini
[Service]
User=nic
Group=nic
WorkingDirectory=/opt/hearth
Environment="ENTITY_HOME=/home/nic/.hearth"
ExecStart=/opt/hearth/venv/bin/python /opt/hearth/main.py serve --host 0.0.0.0 --port 8420
```

### Change Port

Edit the service file:
```bash
sudo nano /etc/systemd/system/hearth.service
```

Change `--port 8420` to your desired port, then:
```bash
sudo systemctl daemon-reload
sudo systemctl restart hearth
```

### Change User

If running as a different user, update:
- `User=` and `Group=`
- `ENTITY_HOME=`

Then reload and restart.

---

## Accessing Services

### Web UI

Open browser to:
- http://localhost:8420/ (if running locally)
- http://YOUR_SERVER_IP:8420/ (if on remote server)

Pages:
- `/` - Chat interface
- `/tasks` - Task management
- `/skills` - Skills library
- `/projects` - Project tracking
- `/proposals` - Review proposals
- `/status` - System status
- `/reflections` - Past reflections
- `/debug` - Debug & introspection
- `/config` - Configuration

### REST API

Base URL: `http://localhost:8420/api/`

Interactive docs: `http://localhost:8420/api/docs`

Example usage:
```bash
# Get health
curl http://localhost:8420/api/health

# List tasks
curl http://localhost:8420/api/tasks

# Create task
curl -X POST http://localhost:8420/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "My task", "priority": 2}'

# Spawn subagent
curl -X POST http://localhost:8420/api/subagents \
  -H "Content-Type: application/json" \
  -d '{"task": "Do something", "agent_type": "grok"}'
```

---

## Troubleshooting

### Service won't start

```bash
# Check status
sudo systemctl status hearth

# Check logs
sudo journalctl -u hearth -n 50

# Common issues:
# - Port already in use: Change port in service file
# - Missing dependencies: /opt/hearth/venv/bin/pip install -r requirements.txt
# - Permission issues: Check User/Group in service file
```

### Port already in use

```bash
# Find what's using port 8420
sudo lsof -i :8420

# Kill it
sudo kill <PID>

# Or change Hearth's port
```

### Check if running

```bash
# Via systemd
sudo systemctl is-active hearth

# Via process
ps aux | grep hearth

# Via network
curl http://localhost:8420/api/health
```

### Can't access from other machines

Check firewall:
```bash
# Ubuntu/Debian
sudo ufw allow 8420/tcp

# CentOS/RHEL
sudo firewall-cmd --add-port=8420/tcp --permanent
sudo firewall-cmd --reload
```

---

## Alternative: Run Components Separately

If you prefer to run components separately (not recommended):

```bash
# Just Nightshift daemon
hearth daemon

# Just Web UI (no API, no daemon)
hearth web --port 8420

# Just REST API (no Web UI, no daemon)
python -m core.api
```

But the unified service (`hearth serve`) is recommended for production.

---

## Development vs Production

### Development

```bash
# Run manually in foreground
hearth serve

# See logs in terminal
# Ctrl+C to stop
```

### Production

```bash
# Install as service
sudo /opt/hearth/install-service.sh

# Starts automatically on boot
# Logs go to journald
# Restart on failure
```

---

## Summary

**Recommended setup:**

1. Install service: `sudo /opt/hearth/install-service.sh`
2. Start it: `sudo systemctl start hearth`
3. Enable auto-start: Already done by install script
4. Access Web UI: http://YOUR_SERVER:8420/
5. Access REST API: http://YOUR_SERVER:8420/api/

**One service, everything included. Simple and clean.**
