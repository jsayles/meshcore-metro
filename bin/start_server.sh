#!/bin/bash
# MeshCore METRO - Server Start Script

# Get to project directory
cd "$(dirname "$0")/.."

# Check if SSL certificates exist
if [ ! -f "ssl/key.pem" ] || [ ! -f "ssl/cert.pem" ]; then
    echo "Error: SSL certificates not found. Please run bin/pi_install.sh first."
    exit 1
fi

# Build the URL
HOSTNAME=$(hostname)
URL="https://${HOSTNAME}.local:8443/"

echo "Starting MeshCore METRO server with HTTPS..."
echo ""
echo "Server will be available at:"
echo "  $URL"
echo ""

# Generate QR code if qrencode is available
if command -v qrencode &> /dev/null; then
    echo "Scan this QR code with your phone:"
    echo ""
    qrencode -t ANSIUTF8 "$URL"
    echo ""
else
    echo "Tip: Install qrencode to display a QR code for easy mobile access:"
    echo "  sudo apt install qrencode"
    echo ""
fi

echo "Press Ctrl+C to stop the server"
echo ""

# Start daphne with HTTPS
uv run daphne -e ssl:8443:privateKey=ssl/key.pem:certKey=ssl/cert.pem metro.asgi:application
