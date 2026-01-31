#!/usr/bin/env bash
set -euo pipefail

echo "=== Homestead Setup ==="
echo ""

# Create data directories
HOMESTEAD_DIR="${HOMESTEAD_DATA_DIR:-$HOME/.homestead}"
echo "Creating data directories at $HOMESTEAD_DIR..."
mkdir -p "$HOMESTEAD_DIR"/{scratchpad,skills,steward,almanac}

# Copy .env files if they don't exist
for pkg in packages/herald manor manor/api; do
    if [ -f "$pkg/.env.example" ] && [ ! -f "$pkg/.env" ]; then
        cp "$pkg/.env.example" "$pkg/.env"
        echo "Created $pkg/.env (edit with your values)"
    fi
done

# Copy lore templates if they don't exist
for tmpl in lore/*.md.example; do
    target="${tmpl%.example}"
    if [ ! -f "$target" ]; then
        cp "$tmpl" "$target"
        echo "Created $target from template"
    fi
done

# Copy MCP config template
if [ -f "manor/mcp-config.json.example" ] && [ ! -f "manor/mcp-config.json" ]; then
    # Replace relative path with absolute venv path
    MANOR_DIR="$(cd manor && pwd)"
    sed "s|\.venv/bin/python3|${MANOR_DIR}/.venv/bin/python3|" \
        manor/mcp-config.json.example > manor/mcp-config.json
    echo "Created manor/mcp-config.json (absolute path: $MANOR_DIR)"
fi

# Python venv for packages
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# Install Python packages
echo "Installing Python dependencies..."
pip install -q aiogram python-dotenv httpx
pip install -q fastapi uvicorn websockets

# Install packages
pip install -q -e packages/common 2>/dev/null || true
pip install -q -e packages/herald 2>/dev/null || true
pip install -q -e packages/mcp-homestead 2>/dev/null || true

# Node.js for Manor
if [ -d "manor" ] && command -v npm &> /dev/null; then
    echo "Installing Manor frontend dependencies..."
    cd manor && npm install && cd ..
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit packages/herald/.env with your Telegram bot token"
echo "  2. Edit manor/api/.env and manor/.env if using the web UI"
echo "  3. Customize lore/ files to personalize your AI"
echo "  4. Run herald:  cd packages/herald && python -m herald.main"
echo "  5. Run manor:   cd manor && npm run dev  (frontend)"
echo "                  cd manor/api && uvicorn main:app --port 8700  (backend)"
