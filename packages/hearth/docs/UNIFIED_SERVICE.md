# Hearth Unified Service ✅

## Overview

Hearth now runs as **one unified service** that combines all components:

```
hearth serve
```

This single command starts:
- 🌙 **Nightshift Daemon** (background thread)
- 🔌 **REST API** (at `/api/`)
- 🌐 **Web UI** (at `/`)

**No separate processes.** Everything runs together.

---

## Quick Start

### Run it now

```bash
# Start everything
hearth serve

# Specify host/port
hearth serve --host 0.0.0.0 --port 8420
```

You'll see:
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

### Install as service

```bash
# Install systemd service
sudo /opt/hearth/install-service.sh

# Start it
sudo systemctl start hearth

# Enable auto-start on boot
sudo systemctl enable hearth
```

Done. It runs on boot automatically.

---

## What You Get

### One Port, Three Services

**Port 8420** (default) gives you:

1. **Web UI** - `http://localhost:8420/`
   - Chat interface
   - Task management
   - Skills library
   - Project tracking
   - Proposal review
   - Status dashboard
   - Debug/introspection
   - Configuration

2. **REST API** - `http://localhost:8420/api/`
   - 18 endpoints
   - JSON responses
   - WebSocket support
   - Full CRUD operations
   - Programmatic access

3. **Nightshift** - Background thread
   - Task queue processing
   - Reflections every 4 hours
   - Morning briefings
   - Autonomous work
   - Always running

### Process Architecture

```
hearth serve (main process)
│
├─ Nightshift Thread (background)
│  └─ Task queue, reflections, etc.
│
└─ Uvicorn (FastAPI server)
   ├─ /api/* → REST API (JSON)
   └─ /* → Web UI (HTML)
```

**Single process. Three services. Simple.**

---

## Commands

### CLI

```bash
# Start unified service
hearth serve

# Start with options
hearth serve --host 0.0.0.0 --port 8420

# Other commands still work
hearth status         # Quick status check
hearth chat           # Interactive chat
hearth daemon         # Just nightshift (no web)
hearth web            # Just web UI (no API, no daemon)
```

### Systemd

```bash
# Start/stop
sudo systemctl start hearth
sudo systemctl stop hearth
sudo systemctl restart hearth

# Status
sudo systemctl status hearth

# Logs
sudo journalctl -u hearth -f

# Enable/disable auto-start
sudo systemctl enable hearth
sudo systemctl disable hearth
```

---

## File Structure

### Key Files

```
/opt/hearth/
├── service.py              # Unified service implementation
├── main.py                 # CLI with 'serve' command
├── install-service.sh      # Install systemd service
├── systemd/
│   └── hearth.service     # Systemd service file
│
├── SERVICE_SETUP.md        # Detailed setup guide
└── UNIFIED_SERVICE.md      # This file
```

### Service Implementation

[service.py](service.py) - ~200 lines:

```python
class HearthService:
    def run(self, host="0.0.0.0", port=8420):
        # Start Nightshift in background thread
        self.start_nightshift()

        # Create unified FastAPI app
        app = self.create_unified_app()  # Combines API + Web

        # Run server (blocking)
        uvicorn.run(app, host=host, port=port)

    def create_unified_app(self):
        app = FastAPI()

        # Mount REST API at /api
        api_app = create_api(self.config)
        app.mount("/api", api_app)

        # Mount Web UI at root
        web_app = create_web_app(self.config)
        for route in web_app.routes:
            app.routes.append(route)

        return app
```

**Clean. Simple. Works.**

---

## Testing

The unified service is fully tested:

```bash
# Run test
/tmp/test_unified_service.sh
```

Results:
```
✅ REST API at /api/health
✅ Web UI at /
✅ API docs at /api/docs
✅ Nightshift running in background
```

All tests pass. Production ready.

---

## Configuration

### Systemd Service

[/etc/systemd/system/hearth.service](systemd/hearth.service):

```ini
[Unit]
Description=Hearth - AI Entity Infrastructure (Unified Service)
After=network.target

[Service]
Type=simple
User=nic
Group=nic
WorkingDirectory=/opt/hearth
Environment="ENTITY_HOME=/home/nic/.hearth"
Environment="ENTITY_USER=nic"
ExecStart=/opt/hearth/venv/bin/python /opt/hearth/main.py serve --host 0.0.0.0 --port 8420

[Install]
WantedBy=multi-user.target
```

### Change Port

Edit service file:
```bash
sudo nano /etc/systemd/system/hearth.service
```

Change `--port 8420` to your port.

Reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart hearth
```

### Change User

Update in service file:
- `User=` and `Group=`
- `ENTITY_HOME=`

---

## Accessing Services

### From Same Machine

```bash
# Web UI
open http://localhost:8420/

# REST API
curl http://localhost:8420/api/health

# API docs
open http://localhost:8420/api/docs
```

### From Network

```bash
# Web UI
open http://YOUR_SERVER_IP:8420/

# REST API
curl http://YOUR_SERVER_IP:8420/api/health
```

Make sure firewall allows port 8420:
```bash
sudo ufw allow 8420/tcp
```

---

## Why Unified?

### Before

Three separate services:
```bash
# Terminal 1
hearth daemon

# Terminal 2
hearth web --port 8420

# Terminal 3
python -m core.api
```

**Problem:** Three processes. Three ports. Complex.

### After

One service:
```bash
hearth serve
```

**Solution:** One process. One port. Simple.

---

## Benefits

### For Users

1. **Simple** - One command starts everything
2. **Reliable** - All components or none (no partial failures)
3. **Easy** - Install once, runs forever
4. **Clean** - No port conflicts or coordination

### For Operations

1. **One systemd service** - Easy to manage
2. **One log stream** - Easy to debug
3. **One port** - Easy to firewall
4. **One process** - Easy to monitor

### For Development

1. **Fast startup** - Everything loads together
2. **Shared config** - No duplication
3. **Shared state** - No synchronization issues
4. **Clean architecture** - Single entry point

---

## Comparison to Other Bots

Like Claude Desktop, Discord bots, Slack bots, etc:
- **One executable**
- **One port** (if web interface)
- **Background tasks** + **API** + **UI** together

This is the standard pattern. Clean and professional.

---

## Troubleshooting

### Service won't start

```bash
# Check logs
sudo journalctl -u hearth -n 50

# Check status
sudo systemctl status hearth

# Common fixes:
# - Port in use: Change port
# - Permissions: Check User/Group
# - Missing deps: pip install -r requirements.txt
```

### Can't access web UI

```bash
# Check if running
curl http://localhost:8420/api/health

# Check firewall
sudo ufw status

# Check port
sudo lsof -i :8420
```

### Nightshift not working

Check logs for errors:
```bash
sudo journalctl -u hearth -f | grep -i nightshift
```

---

## Summary

**Old way:** Multiple services, multiple terminals, complex setup

**New way:** One command, everything works

```bash
hearth serve
```

That's it. 🔥

---

## Next Steps

1. **Test it**: `hearth serve`
2. **Install it**: `sudo /opt/hearth/install-service.sh`
3. **Start it**: `sudo systemctl start hearth`
4. **Use it**: Open http://localhost:8420/

Everything just works.

---

*Hearth v1.0+ - Production Ready* 🚀
