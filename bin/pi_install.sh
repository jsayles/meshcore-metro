#!/bin/bash
# MeshCore METRO - Raspberry Pi Installation Script
# Simple setup for fresh Raspberry Pi deployment

set -e  # Exit on any error

echo ""
echo "=================================="
echo "MeshCore METRO - Pi Installation"
echo "=================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
   echo "Please do not run as root/sudo. Script will ask for sudo when needed."
   exit 1
fi

# Update system
echo "=> Updating system packages..."
sudo apt update

# Install system dependencies
echo "=> Installing system dependencies..."
sudo apt install -y \
    postgresql \
    postgresql-contrib \
    postgis \
    redis-server \
    python3-dev \
    libpq-dev \
    gdal-bin \
    qrencode \
    avahi-daemon

# Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "=> Installing uv (Python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Add uv to PATH in shell profile for persistence
    SHELL_RC="$HOME/.bashrc"
    if [ -n "$ZSH_VERSION" ]; then
        SHELL_RC="$HOME/.zshrc"
    fi

    # Check if PATH is already in shell profile
    if ! grep -q '.local/bin' "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# Added by MeshCore METRO installer" >> "$SHELL_RC"
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
        echo "   Added uv to PATH in $SHELL_RC"
    fi
fi

# Ensure uv is in PATH for this script
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

# Verify uv is available
if ! command -v uv &> /dev/null; then
    echo "ERROR: uv installation failed or not in PATH"
    echo "Please restart your shell and run the script again, or manually add uv to PATH:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    exit 1
fi

# Configure WiFi for phone hotspot (additive - doesn't remove existing networks)
echo ""
echo "=> Configuring WiFi connection to phone hotspot..."
echo ""
echo "For field operations, the Pi needs to connect to your phone's WiFi hotspot."
echo "This will ADD a new WiFi connection without removing any existing networks."
echo ""

# Scan for available WiFi networks
echo "Scanning for available WiFi networks..."
sudo nmcli dev wifi rescan 2>/dev/null || true
sleep 2

# Get list of SSIDs (excluding the header and empty lines)
mapfile -t WIFI_NETWORKS < <(sudo nmcli -t -f SSID dev wifi list | grep -v '^$' | sort -u)

if [ ${#WIFI_NETWORKS[@]} -gt 0 ]; then
    echo ""
    echo "Available WiFi networks:"
    echo "  0) Skip WiFi configuration"
    echo "  1) Enter SSID manually"
    for i in "${!WIFI_NETWORKS[@]}"; do
        echo "  $((i+2))) ${WIFI_NETWORKS[$i]}"
    done
    echo ""
    read -p "Select your phone's hotspot (0-$((${#WIFI_NETWORKS[@]}+1))): " WIFI_CHOICE

    if [ "$WIFI_CHOICE" = "0" ]; then
        echo "   Skipping WiFi configuration"
        HOTSPOT_SSID=""
    elif [ "$WIFI_CHOICE" = "1" ]; then
        read -p "Enter your phone's hotspot SSID: " HOTSPOT_SSID
    elif [ "$WIFI_CHOICE" -ge 2 ] && [ "$WIFI_CHOICE" -le $((${#WIFI_NETWORKS[@]}+1)) ]; then
        HOTSPOT_SSID="${WIFI_NETWORKS[$((WIFI_CHOICE-2))]}"
        echo "Selected: $HOTSPOT_SSID"
    else
        echo "   Invalid selection, skipping WiFi configuration"
        HOTSPOT_SSID=""
    fi
else
    echo "   No WiFi networks found. You can configure manually later."
    read -p "Enter your phone's hotspot SSID [or press Enter to skip]: " HOTSPOT_SSID
fi

if [ -n "$HOTSPOT_SSID" ]; then
    read -sp "Enter password for '$HOTSPOT_SSID': " HOTSPOT_PASSWORD
    echo ""
    echo ""

    if [ -n "$HOTSPOT_PASSWORD" ]; then
        echo "=> Adding WiFi connection profile..."

        # Use nmcli to add connection (Raspberry Pi OS Bookworm uses NetworkManager)
        # This is additive - it doesn't remove or modify existing connections
        if sudo nmcli connection add \
            con-name "phone-hotspot" \
            ifname wlan0 \
            type wifi \
            ssid "$HOTSPOT_SSID" \
            wifi-sec.key-mgmt wpa-psk \
            wifi-sec.psk "$HOTSPOT_PASSWORD" \
            autoconnect yes \
            autoconnect-priority 10; then
            echo "   WiFi connection 'phone-hotspot' added successfully"
            echo "   Pi will auto-connect to '$HOTSPOT_SSID' when available"
            echo "   Your existing WiFi connections are still configured"
        else
            echo "   ERROR: Failed to add WiFi connection"
            echo "   You may need to configure WiFi manually using:"
            echo "   sudo nmcli device wifi connect \"$HOTSPOT_SSID\" password \"your-password\""
        fi
    else
        echo "   Skipping - no password provided"
    fi
fi

# Enable Avahi for mDNS
echo "=> Enabling Avahi (mDNS) for hostname discovery..."
sudo systemctl enable avahi-daemon 2>/dev/null || true
sudo systemctl start avahi-daemon 2>/dev/null || true
echo "   Pi will be accessible at: https://$(hostname).local:8443"

# Setup database (run from /tmp to avoid directory permission warnings)
echo "=> Setting up PostgreSQL database..."
(cd /tmp && sudo -u postgres psql -c "DROP DATABASE IF EXISTS metrodb;" 2>/dev/null) || true
(cd /tmp && sudo -u postgres createdb metrodb)
(cd /tmp && sudo -u postgres psql metrodb -c "CREATE EXTENSION IF NOT EXISTS postgis;")

# Create a database user for the current system user (for peer authentication)
echo "=> Creating database user for $USER..."
(cd /tmp && sudo -u postgres psql -c "DROP USER IF EXISTS $USER;" 2>/dev/null) || true
(cd /tmp && sudo -u postgres psql -c "CREATE USER $USER WITH PASSWORD '';")
(cd /tmp && sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE metrodb TO $USER;")
(cd /tmp && sudo -u postgres psql metrodb -c "GRANT ALL ON SCHEMA public TO $USER;")

# Install Python dependencies first
echo "=> Installing Python dependencies..."
uv sync

# Create .env file (optional - for production settings)
echo "=> Creating .env configuration..."
cat > .env << EOF
SECRET_KEY=$(uv run python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
DEBUG=False
ALLOWED_HOSTS=*
EOF
echo "   .env file created with production settings"

echo "=> Running database migrations..."
uv run python manage.py migrate

echo "=> Collecting static files..."
uv run python manage.py collectstatic --noinput

echo "=> Finding USB radio..."
uv run python manage.py find_usb_radio --save || echo "No USB radio found - you can configure it later"

echo "=> Generating self-signed SSL certificate..."
mkdir -p ssl
HOSTNAME=$(hostname)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/key.pem \
    -out ssl/cert.pem \
    -subj "/C=US/ST=State/L=City/O=MeshCore/OU=IT/CN=$HOSTNAME.local" \
    -addext "subjectAltName=DNS:$HOSTNAME.local,DNS:$HOSTNAME,DNS:localhost,IP:127.0.0.1" 2>/dev/null
echo "   Certificate generated in ssl/ directory"

echo ""
echo "=================================="
echo "Installation Complete!"
echo "=================================="
echo ""
echo "IMPORTANT: To use commands, either:"
echo "  1. Restart your terminal, OR"
echo "  2. Run: source ~/.bashrc"
echo ""
echo "Before starting, load radio data from your USB companion:"
echo "  uv run python manage.py load_radio_data"
echo ""
echo "To start the server:"
echo "  bin/start_server.sh"
echo ""
echo "Then visit: https://$(hostname).local:8443/"
echo ""
echo "IMPORTANT: Your browser will show a security warning for the self-signed"
echo "certificate. Click 'Advanced' and 'Proceed' to accept it."
echo ""
echo "Create admin user (optional):"
echo "  uv run python manage.py createsuperuser"
echo ""
