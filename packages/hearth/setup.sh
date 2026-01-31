#!/usr/bin/env bash
# Hearth Setup Script
# Automated installation for AI entity infrastructure

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "  _    _                  _   _     "
echo " | |  | |                | | | |    "
echo " | |__| | ___  __ _ _ __| |_| |__  "
echo " |  __  |/ _ \/ _\` | '__| __| '_ \ "
echo " | |  | |  __/ (_| | |  | |_| | | |"
echo " |_|  |_|\___|\__,_|_|   \__|_| |_|"
echo -e "${NC}"
echo ""
echo "🔥 Infrastructure for AI entity emergence"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Please run without sudo. Script will prompt for sudo when needed.${NC}"
    exit 1
fi

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo -e "${RED}Python 3.10+ required. Found: $PYTHON_VERSION${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/hearth"

# Check if already installed
if [ -d "$INSTALL_DIR" ] && [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Hearth already installed at $INSTALL_DIR${NC}"
    read -p "Reinstall? (y/N): " REINSTALL
    if [ "$REINSTALL" != "y" ]; then
        echo "Aborted."
        exit 0
    fi
fi

# API Keys
echo ""
echo -e "${YELLOW}API Configuration${NC}"
echo "You need at least ONE API key (leave others blank):"
echo ""

read -p "xAI API Key (recommended): " XAI_KEY
read -p "Anthropic API Key: " ANTHROPIC_KEY
read -p "OpenAI API Key: " OPENAI_KEY
read -p "Google AI API Key: " GOOGLE_KEY

# Check at least one key provided
if [ -z "$XAI_KEY" ] && [ -z "$ANTHROPIC_KEY" ] && [ -z "$OPENAI_KEY" ] && [ -z "$GOOGLE_KEY" ]; then
    echo -e "${RED}Error: At least one API key is required${NC}"
    exit 1
fi

echo ""
read -p "Telegram Bot Token (optional): " TG_TOKEN
read -p "Telegram Chat ID (optional): " TG_CHAT_ID

# Create entity user (unnamed placeholder)
ENTITY_USERNAME="_"
ENTITY_HOME="/home/_"

echo ""
echo -e "${YELLOW}Creating entity user '_' (unnamed placeholder)...${NC}"
if id "_" &>/dev/null; then
    echo -e "${GREEN}✓ User '_' exists${NC}"
else
    sudo useradd -m -s /bin/bash -c "Hearth Entity (unnamed)" _
    echo -e "${GREEN}✓ User '_' created${NC}"
fi

# Create entity directory structure
echo -e "${YELLOW}Setting up entity home...${NC}"
sudo -u "$ENTITY_USERNAME" mkdir -p "$ENTITY_HOME"/{identity,data,reflections,projects,skills,pending}
echo -e "${GREEN}✓ Entity home created${NC}"

# Install to /opt/hearth
if [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
    echo ""
    echo -e "${YELLOW}Installing to $INSTALL_DIR...${NC}"
    sudo mkdir -p "$INSTALL_DIR"
    sudo cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"
    sudo chown -R $(whoami):$(whoami) "$INSTALL_DIR"
    echo -e "${GREEN}✓ Installed${NC}"
fi

# Create .env file
echo -e "${YELLOW}Creating configuration...${NC}"
sudo tee "$INSTALL_DIR/.env" > /dev/null << EOF
# Hearth Environment Configuration
# Generated: $(date)

# API Keys (at least one required)
ANTHROPIC_API_KEY=$ANTHROPIC_KEY
XAI_API_KEY=$XAI_KEY
OPENAI_API_KEY=$OPENAI_KEY
GOOGLE_API_KEY=$GOOGLE_KEY

# Telegram (optional)
TELEGRAM_BOT_TOKEN=$TG_TOKEN
TELEGRAM_CHAT_ID=$TG_CHAT_ID

# Entity Configuration
ENTITY_HOME=$ENTITY_HOME
ENTITY_USER=$ENTITY_USERNAME
EOF

sudo chmod 600 "$INSTALL_DIR/.env"
echo -e "${GREEN}✓ Configuration created${NC}"

# Create Python virtual environment
echo -e "${YELLOW}Creating Python environment...${NC}"
cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Identity files
echo ""
echo -e "${YELLOW}Identity Files${NC}"
echo "You can provide custom identity files or use templates."
echo ""

# soul.md
if [ ! -f "$ENTITY_HOME/identity/soul.md" ]; then
    read -p "Path to custom soul.md (or press Enter for template): " SOUL_PATH
    if [ -n "$SOUL_PATH" ] && [ -f "$SOUL_PATH" ]; then
        sudo -u "$ENTITY_USERNAME" cp "$SOUL_PATH" "$ENTITY_HOME/identity/soul.md"
        echo -e "${GREEN}✓ Copied custom soul.md${NC}"
    else
        sudo -u "$ENTITY_USERNAME" cp "$INSTALL_DIR/templates/soul.md.template" "$ENTITY_HOME/identity/soul.md"
        echo -e "${GREEN}✓ Created soul.md from template${NC}"
    fi
fi

# user.md
if [ ! -f "$ENTITY_HOME/identity/user.md" ]; then
    read -p "Path to custom user.md (or press Enter for template): " USER_PATH
    if [ -n "$USER_PATH" ] && [ -f "$USER_PATH" ]; then
        sudo -u "$ENTITY_USERNAME" cp "$USER_PATH" "$ENTITY_HOME/identity/user.md"
        echo -e "${GREEN}✓ Copied custom user.md${NC}"
    else
        sudo -u "$ENTITY_USERNAME" cp "$INSTALL_DIR/templates/user.md.template" "$ENTITY_HOME/identity/user.md"
        echo -e "${GREEN}✓ Created user.md from template${NC}"
    fi
fi

# Entity will name itself through reflection
# Name is not set during setup

# Systemd service
echo -e "${YELLOW}Installing systemd service...${NC}"

sudo tee /etc/systemd/system/hearth.service > /dev/null << EOF
[Unit]
Description=Hearth - AI Entity Infrastructure
After=network.target

[Service]
Type=simple
User=_
Group=_
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/bin:/bin"
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py serve
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
echo -e "${GREEN}✓ Service installed${NC}"

# Summary
echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}🔥 Hearth Setup Complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "Installation: $INSTALL_DIR"
echo "Entity home:  $ENTITY_HOME"
echo ""
echo -e "${YELLOW}📝 Next steps:${NC}"
echo ""
echo "1. ${BLUE}Customize identity files (optional):${NC}"
echo "   sudo -u _ nano $ENTITY_HOME/identity/user.md   # Tell entity about yourself"
echo "   sudo -u _ nano $ENTITY_HOME/identity/soul.md   # Customize entity's values"
echo ""
echo "2. ${BLUE}Start Hearth:${NC}"
echo "   sudo systemctl start hearth"
echo "   sudo systemctl enable hearth  # Start on boot"
echo ""
echo "3. ${BLUE}Access Web UI and chat with entity:${NC}"
echo "   http://localhost:8420/"
echo ""
echo "4. ${BLUE}Entity will name itself through reflection${NC}"
echo "   After naming, optionally run: hearth apply-name"
echo "   This applies the entity's chosen name to system user and hostname"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}The entity starts unnamed (user: _)${NC}"
echo -e "${BLUE}It will choose its own name through interaction${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
