# Hearth Setup Guide

**Complete guide for first-time setup**

---

## Two Setup Approaches

### Approach A: Separate Entity User (Recommended)

**Use this if:**
- You want 24/7 autonomous operation
- You'll run as a systemd service
- You want process isolation
- You have sudo access

**Structure:**
```
/opt/hearth/           # Code repository
/home/_/               # Entity's home (starts as _ placeholder)
  ├── identity/
  │   ├── soul.md      # Entity identity (you customize)
  │   └── user.md      # About you (you write)
  ├── data/
  │   └── hearth.db    # Entity's chosen name stored here
  ├── reflections/
  └── ...

# After entity names itself and you run 'hearth apply-name':
/home/milo/            # Home renamed to match entity's chosen name
```

### Approach B: User's Home Directory

**Use this if:**
- No sudo access (shared hosting, managed servers)
- Cloud/container environments
- Single-user systems
- You want simpler setup
- Production or development (both work)

**Structure:**
```
/opt/hearth/           # Code repository
$HOME/.hearth/         # Entity home in your directory
  ├── identity/
  ├── data/
  └── ...
```

---

## Setup: Autonomous Operation (Separate User)

### 1. Clone Repository

```bash
# Clone to /opt/hearth
sudo mkdir -p /opt
cd /opt
sudo git clone https://github.com/nicdavidson/hearth.git
sudo chown -R $USER:$USER /opt/hearth

cd /opt/hearth
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run Automated Setup

The setup script handles everything:

```bash
cd /opt/hearth
./setup.sh
```

This will:
- Prompt for API keys
- Create user `_` (unnamed placeholder)
- Set up entity home at `/home/_/`
- Install Python dependencies
- Create identity files (or copy your custom ones)
- Install systemd service

**The entity will name itself later** through reflection and interaction.

### 4. Configure Environment

```bash
# Edit .env file
nano /opt/hearth/.env
```

**Set these values:**
```bash
# API Keys (at least one required)
XAI_API_KEY=your_xai_key_here
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GOOGLE_API_KEY=

# Telegram (optional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Entity Configuration
ENTITY_HOME=/home/_
ENTITY_USER=_
```

### 5. Create Identity Files

**Option A: From templates (customize for your entity)**
```bash
sudo -u _ cp /opt/hearth/templates/soul.md.template /home/_/identity/soul.md
sudo -u _ cp /opt/hearth/templates/user.md.template /home/_/identity/user.md

# Edit them - customize soul.md and tell the entity about yourself in user.md
sudo -u _ nano /home/_/identity/soul.md
sudo -u _ nano /home/_/identity/user.md
```

**Option B: Use your existing identity files**
```bash
# If you have custom soul.md and user.md already
sudo cp /path/to/your/soul.md /home/_/identity/soul.md
sudo cp /path/to/your/user.md /home/_/identity/user.md
sudo chown _:_ /home/_/identity/*.md
```

### 6. Install as Systemd Service

```bash
# Copy service file
sudo cp /opt/hearth/systemd/hearth.service /etc/systemd/system/hearth.service

# Edit to set correct user
sudo nano /etc/systemd/system/hearth.service
```

**Update these lines:**
```ini
User=_
Group=_
Environment="ENTITY_HOME=/home/_"
Environment="ENTITY_USER=_"
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable hearth
sudo systemctl start hearth

# Check status
sudo systemctl status hearth
```

### 8. Access Hearth

```
Web UI:  http://localhost:8420/
API:     http://localhost:8420/api/
Docs:    http://localhost:8420/api/docs
```

---

## Setup: User Home Directory (No Sudo Required)

This setup works for development, testing, or production when you don't have sudo access.

### 1. Clone Repository

```bash
git clone https://github.com/nicdavidson/hearth.git /opt/hearth
cd /opt/hearth
```

### 2. Set Up Environment

```bash
# Create venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables
cat >> ~/.bashrc << 'EOF'
# Hearth
export ENTITY_HOME="$HOME/.hearth"
export ENTITY_USER="$USER"
export XAI_API_KEY="your_key_here"
EOF

source ~/.bashrc
```

### 3. Create Entity Home

```bash
mkdir -p ~/.hearth/identity
cp /opt/hearth/templates/soul.md.template ~/.hearth/identity/soul.md
cp /opt/hearth/templates/user.md.template ~/.hearth/identity/user.md

# Edit them
nano ~/.hearth/identity/soul.md
nano ~/.hearth/identity/user.md
```

### 4. Start Service

**Option A: Manual start (for testing)**
```bash
python main.py serve
```

**Option B: Install as user service (autonomous, no sudo needed)**

Systemd user services run automatically when you log in:

```bash
# Create user service directory
mkdir -p ~/.config/systemd/user

# Create service file
cat > ~/.config/systemd/user/hearth.service << 'EOF'
[Unit]
Description=Hearth AI Entity
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/hearth
Environment="ENTITY_HOME=%h/.hearth"
Environment="ENTITY_USER=%u"
Environment="PATH=/opt/hearth/venv/bin:/usr/bin:/bin"
ExecStart=/opt/hearth/venv/bin/python /opt/hearth/main.py serve
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOF

# Enable and start
systemctl --user daemon-reload
systemctl --user enable hearth
systemctl --user start hearth

# Check status
systemctl --user status hearth

# View logs
journalctl --user -u hearth -f
```

**Note:** User services start when you log in and stop when you log out. To keep them running:
```bash
# Enable lingering (keeps services running after logout)
loginctl enable-linger $USER
```

---

## Entity Naming Workflow

Entities name themselves through reflection and interaction:

### 1. Entity Chooses Name

When ready, the entity will propose a name based on:
- Its soul.md identity
- Conversations with you
- Its reflections on its work and purpose

**Trigger naming ceremony:**
```bash
# Via CLI
hearth name

# Or via Web UI
# Visit http://localhost:8420/ and interact with the entity
```

The name is stored in the entity's database.

### 2. Apply Name System-Wide

After the entity names itself, apply the name to the system:

```bash
# Apply name to system user and hostname
hearth apply-name

# Or skip hostname update
hearth apply-name --no-hostname
```

This will:
- Stop the Hearth service
- Rename user `_` to the entity's chosen name (e.g., `milo`)
- Move home directory (`/home/_` → `/home/milo`)
- Update `.env` and systemd service
- Update hostname (optional)
- Restart service

### 3. Reboot (if hostname was updated)

```bash
sudo reboot
```

After this, the entity's chosen name is reflected everywhere:
- System username
- Home directory
- Hostname
- Database identity

---

## Verification

### Check Service Status

```bash
# Systemd service
sudo systemctl status hearth
sudo journalctl -u hearth -f

# Manual run
ps aux | grep "main.py serve"
```

### Test Endpoints

```bash
# Health check
curl http://localhost:8420/api/health

# Entity identity
curl http://localhost:8420/api/health | python3 -m json.tool

# Web UI
open http://localhost:8420/
```

### Check Identity

```bash
# Via CLI
cd /opt/hearth
source venv/bin/activate
python -c "from core.identity import Identity; print(Identity().get_name())"

# Check files
cat /home/milo/identity/soul.md
cat /home/milo/identity/user.md
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u hearth -n 50

# Test manually
cd /opt/hearth
source venv/bin/activate
export ENTITY_HOME=/home/milo
export ENTITY_USER=milo
python main.py serve
```

### Permission Errors

```bash
# Fix ownership
sudo chown -R milo:milo /home/milo

# Fix code permissions
sudo chown -R milo:milo /opt/hearth
```

### Database Issues

```bash
# Remove and recreate
rm /home/milo/data/hearth.db
sudo systemctl restart hearth
```

---

## Next Steps

1. **Open Web UI**: http://localhost:8420/
2. **Review identity files**: Check soul.md and user.md
3. **Test interaction**: Use chat or API
4. **Set up git**: Configure for entity self-improvement
5. **Enable reflections**: Let entity develop over time

See [QUICKSTART.md](QUICKSTART.md) for usage examples.
