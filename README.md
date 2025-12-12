# MeshCore METRO

## Mesh Telemetry & Radio Ops

An integrated Django/GeoDjango web application for monitoring and analyzing MeshCore mesh networks.

**Two complementary features:**
1. **Repeater Monitor** - Real-time health monitoring and telemetry tracking
2. **Signal Mapper** - Field survey tool for signal coverage heatmaps

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

# Load radio data
uv run python manage.py load_radio_data

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
# Run with Channels/WebSocket support (REQUIRED for Signal Mapper)
uv run daphne -b 0.0.0.0 -p 8000 metro.asgi:application

# Find connected USB radios
uv run python manage.py find_usb_radio
uv run python manage.py find_usb_radio --save

# Load contacts from USB radio
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

## Related Projects

### MeshCore MQTT Broker
**Repository:** https://github.com/michaelhart/meshcore-mqtt-broker

**Important Note:** The main developer (Tree) runs the main meshcore-analyzer website. This MQTT broker project may have overlapping functionality with our platform. We should coordinate with them as there may be opportunities to merge or integrate our projects in the future.

## Next Steps

- [ ] Fine-tune MeshCore radio API integration 
- [ ] Build Repeater Monitor frontend dashboard
- [ ] Deploy to Raspberry Pi with systemd services
- [ ] Add advanced heatmap interpolation
- [ ] Evaluate integration opportunities with meshcore-mqtt-broker

See full roadmap in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
