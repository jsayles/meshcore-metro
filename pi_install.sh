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
    gdal-bin

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

echo ""
echo "=================================="
echo "Installation Complete!"
echo "=================================="
echo ""
echo "IMPORTANT: To use uv commands, either:"
echo "  1. Restart your terminal, OR"
echo "  2. Run: source ~/.bashrc"
echo ""
echo "Before starting, load radio data from your USB companion:"
echo "  uv run python manage.py load_radio_data"
echo ""
echo "Then start the server:"
echo "  uv run daphne -b 0.0.0.0 -p 8000 metro.asgi:application"
echo ""
echo "Then visit: http://$(hostname -I | awk '{print $1}'):8000/"
echo ""
echo "Create admin user (optional):"
echo "  uv run python manage.py createsuperuser"
echo ""
