#!/bin/bash
# MeshCore METRO - Install systemd service for auto-start

set -e

echo ""
echo "=================================="
echo "MeshCore METRO - Service Installer"
echo "=================================="
echo ""

# Get the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
USER=$(whoami)

echo "Installing systemd service..."
echo "Project directory: $PROJECT_DIR"
echo "Running as user: $USER"
echo ""

# Create the systemd service file
sudo tee /etc/systemd/system/meshcore-metro.service > /dev/null <<EOF
[Unit]
Description=MeshCore METRO - Mesh Telemetry & Radio Ops
After=network-online.target postgresql.service redis-server.service
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=/home/$USER/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/$USER/.local/bin/uv run daphne -e ssl:8443:privateKey=$PROJECT_DIR/ssl/key.pem:certKey=$PROJECT_DIR/ssl/cert.pem metro.asgi:application
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable the service
echo "=> Enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable meshcore-metro.service

echo ""
echo "✓ Service installed successfully!"
echo ""
echo "Commands:"
echo "  Start:   sudo systemctl start meshcore-metro"
echo "  Stop:    sudo systemctl stop meshcore-metro"
echo "  Status:  sudo systemctl status meshcore-metro"
echo "  Logs:    sudo journalctl -u meshcore-metro -f"
echo ""
echo "The server will now start automatically on boot!"
echo ""

read -p "Start the service now? (y/n): " START_NOW
if [ "$START_NOW" = "y" ] || [ "$START_NOW" = "Y" ]; then
    sudo systemctl start meshcore-metro
    echo ""
    echo "✓ Service started!"
    echo ""
    echo "Visit: https://$(hostname).local:8443/"
    echo ""
fi
