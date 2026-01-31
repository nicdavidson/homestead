#!/bin/bash
# Install Hearth systemd service

set -e

echo "Installing Hearth systemd service..."

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo: sudo ./install-service.sh"
    exit 1
fi

# Copy service file
echo "Copying service file..."
cp /opt/hearth/systemd/hearth.service /etc/systemd/system/hearth.service

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload

# Enable service
echo "Enabling service..."
systemctl enable hearth.service

echo ""
echo "✅ Hearth service installed!"
echo ""
echo "Commands:"
echo "  sudo systemctl start hearth    # Start the service"
echo "  sudo systemctl stop hearth     # Stop the service"
echo "  sudo systemctl status hearth   # Check status"
echo "  sudo systemctl restart hearth  # Restart the service"
echo "  sudo journalctl -u hearth -f   # View logs (live)"
echo ""
echo "The service will:"
echo "  - Start automatically on boot"
echo "  - Run Nightshift daemon in background"
echo "  - Serve Web UI at http://0.0.0.0:8420/"
echo "  - Serve REST API at http://0.0.0.0:8420/api/"
echo ""
