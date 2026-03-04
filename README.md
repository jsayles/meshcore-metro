# MeshCore METRO

## Mesh Telemetry & Radio Ops

An integrated Django/GeoDjango web application for monitoring and analyzing MeshCore mesh networks.

**Three complementary features:**
1. **Mesh Configuration** - Discover and manage repeater contacts from your radio
2. **Repeater Monitor** - Real-time health monitoring and telemetry tracking
3. **Field Testing** - Field survey tool for signal coverage heatmaps

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full architecture details.

## Quick Start

### Raspberry Pi Installation

For production deployment on a Raspberry Pi:

```bash
# Clone the repository
git clone https://github.com/jsayles/meshcore-metro.git
cd meshcore-metro

# Run the installation script (will prompt for phone hotspot WiFi credentials)
bin/pi_install.sh

# After installation, source ~/.bashrc to update PATH
source ~/.bashrc

# Start the server
bin/start_server.sh
```

The start script will display a QR code - scan it with your phone to access the app!

Visit: `https://<hostname>.local:8443/` (accept the self-signed certificate warning)

**Field Setup:**
1. Turn on your phone's WiFi hotspot
2. Pi will auto-connect (credentials configured during install)
3. Run `bin/start_server.sh` on the Pi
4. Scan the QR code or visit `https://<hostname>.local:8443/` on your phone

**Reconfigure WiFi:** Run `bin/configure_wifi.sh` anytime to add/change your phone's hotspot connection

### Development Setup (Mac/Linux)

- Python 3.14+
- PostgreSQL with PostGIS extension
- Redis server (for WebSocket channels)
- MeshCore radio connected as USB companion

```bash
# 1. Install dependencies
uv sync

# 2. Create database
createdb metrodb
psql metrodb -c "CREATE EXTENSION postgis;"

# 3. Create .env file
cp .env.example .env

# 4. Run migrations
uv run manage.py migrate

# 5. Set up your USB Companion
uv run python manage.py find_usb_radio --save

# 6. Start server (localhost uses HTTP)
uv run daphne -b 0.0.0.0 -p 8000 metro.asgi:application
```

**Browser:**
- Mesh Home: http://localhost:8000/
- Admin: http://localhost:8000/admin/
- API: http://localhost:8000/api/v1/


## Development Commands

```bash
# Run with Channels/WebSocket support (REQUIRED for Field Test)
uv run daphne -b 0.0.0.0 -p 8000 metro.asgi:application

# Find connected USB radios
uv run python manage.py find_usb_radio
uv run python manage.py find_usb_radio --save

# Sync repeater data from radio (telemetry, names, location)
# Run this if repeaters have been renamed and the new name hasn't propagated yet
uv run python manage.py load_radio_data

# Run migrations
uv run python manage.py migrate

# Run tests
uv run python manage.py test --parallel auto

# Manage dependencies
uv pip list --outdated
uv lock --upgrade
uv sync
```

## System Architecture

The application provides three integrated features: Mesh Configuration for managing repeater contacts, Repeater Monitor for real-time telemetry tracking, and Field Testing for signal coverage heatmaps. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed feature specifications and roadmap.

## Related Projects

See [docs/RELATED_PROJECTS.md](docs/RELATED_PROJECTS.md) for a list of MeshCore mapping systems, visualization tools, and related projects in the ecosystem.


## Next Steps

- [ ] Better Installation docs and scripts
- [ ] Improved mobile interface
- [ ] Enhanced Field Test log view and merging.
- [ ] Build Repeater Monitor frontend dashboard
- [ ] Deploy to Raspberry Pi with systemd services
- [ ] Add advanced heatmap interpolation
- [ ] Evaluate integration opportunities with meshcore-mqtt-broker

