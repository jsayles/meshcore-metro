#!/bin/bash
# MeshCore METRO - Raspberry Pi Installation Script
# Simple setup for fresh Raspberry Pi deployment

set -e  # Exit on any error

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
    # Add uv to PATH for this session
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
else
    # Ensure uv is in PATH
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

# Setup database
echo "=> Setting up PostgreSQL database..."
sudo -u postgres psql -c "DROP DATABASE IF EXISTS metrodb;" 2>/dev/null || true
sudo -u postgres createdb metrodb
sudo -u postgres psql metrodb -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# Generate random password for postgres
DB_PASSWORD=$(openssl rand -base64 12)
sudo -u postgres psql -c "ALTER USER postgres PASSWORD '$DB_PASSWORD';"

# Install Python dependencies first
echo "=> Installing Python dependencies..."
uv sync

# Create .env file
echo "=> Creating .env configuration..."
SECRET_KEY=$(uv run python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
cat > .env << EOF
# Database
DATABASE_URL=postgresql://postgres:$DB_PASSWORD@localhost:5432/metrodb

# Django
SECRET_KEY=$SECRET_KEY
DEBUG=False
ALLOWED_HOSTS=*

# Redis
REDIS_URL=redis://localhost:6379/0
EOF

echo "=> Running database migrations..."
uv run python manage.py migrate

echo "=> Finding USB radio..."
uv run python manage.py find_usb_radio --save || echo "No USB radio found - you can configure it later"

echo ""
echo "=================================="
echo "Installation Complete!"
echo "=================================="
echo ""
echo "To start the server:"
echo "  uv run daphne -b 0.0.0.0 -p 8000 metro.asgi:application"
echo ""
echo "Then visit: http://$(hostname -I | awk '{print $1}'):8000/"
echo ""
echo "Create admin user (optional):"
echo "  uv run python manage.py createsuperuser"
echo ""
