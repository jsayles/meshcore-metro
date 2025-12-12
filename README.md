# MeshCore Analytics

An integrated Django/GeoDjango web application for monitoring and analyzing MeshCore mesh networks.

**Two complementary features:**
1. **Repeater Monitor** - Real-time health monitoring and telemetry tracking
2. **Signal Mapper** - Field survey tool for signal coverage heatmaps

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full architecture details.

## Quick Start (Development - Signal Mapper MVP)

**Works on both Laptop and Pi!** You can develop and test everything on your laptop, including with a real MeshCore radio plugged in via USB.

### Prerequisites

- Python 3.14+
- PostgreSQL with PostGIS extension
- Redis server (for WebSocket channels)
- MeshCore radio connected via USB

### Setup

```bash
# 1. Install dependencies
uv sync

# 2. Create database
createdb maxdb
psql maxdb -c "CREATE EXTENSION postgis;"

# 3. Create .env file
cp .env.example .env
```

Edit `.env` and configure:
```bash
# Find your USB radio port:
# Mac: ls /dev/tty.*
# Linux: ls /dev/ttyACM* or ls /dev/ttyUSB*

# Update .env with your port:
SERIAL_PORT=/dev/tty.usbmodem21401  # Your actual device
```

```bash
# 4. Run migrations
uv run manage.py migrate

# 5. Run django
uv run daphne -b 0.0.0.0 -p 8000 max.asgi:application
```

**Browser:**
- Mesh Home: http://localhost:8000/
- Admin: http://localhost:8000/admin/
- API: http://localhost:8000/api/v1/

## Workflow

1. Open http://localhost:8000/ or http://localhost:8000/mapper/?node=<id> in browser
2. **Setup Steps** (3-step checklist):
   - **Step 1 - Repeater**: Select target repeater from dropdown (or pre-selected via URL)
   - **Step 2 - Location Tracking**: Browser requests GPS permission (automatically)
   - **Step 3 - Companion Radio**: Click "Connect" to establish WebSocket connection
3. **Collection** (appears after setup complete):
   - Choose Manual or Continuous mode
   - Click "Collect Now" for single measurement
   - Or set interval and "Start Collection" for continuous measurements
4. **Visualization**: Heatmap automatically updates with new measurements

**Features:**
- Session-based measurement tracking (uses Django session ID)
- Real-time heatmap rendering with color-coded signal strength
- Responsive sidebar (420px) with progress indicators
- Mobile-friendly interface with viewport optimization
- Automatic GPS streaming to Pi via WebSocket
- Map centered on Vancouver, BC by default
- Reads signal data from USB-connected MeshCore radio

## Development Commands

```bash
# Run with Channels/WebSocket support (REQUIRED for Signal Mapper)
uv run daphne -b 0.0.0.0 -p 8000 max.asgi:application

# Find connected USB radios
uv run python manage.py find_usb_radio
uv run python manage.py find_usb_radio --test
uv run python manage.py find_usb_radio --update-env

# Load contacts from USB radio
uv run python manage.py load_radio_data

# Run migrations
uv run python manage.py migrate

# Create superuser
uv run python manage.py createsuperuser

# Run tests
uv run python manage.py test --parallel auto

# Manage dependencies
uv pip list --outdated
uv lock --upgrade
uv sync
```

## Project Structure

```
├── max/                    # Main Django app
│   ├── models.py           # Node, SignalMeasurement, RepeaterStats
│   ├── consumers.py        # WebSocket consumer (GPS/signal)
│   ├── radio_interface.py  # USB radio interface
│   ├── static/max/js/
│   │   ├── pi-connection.js       # WebSocket client
│   │   ├── measurement-collector.js
│   │   ├── heatmap-renderer.js
│   │   └── signal-mapper.js
│   └── templates/
├── api/                    # REST API
├── docs/
│   └── ARCHITECTURE.md     # Full system docs
└── pyproject.toml
```

## API Endpoints

- `GET /api/v1/nodes/` - List active nodes
- `GET/POST /api/v1/measurements/` - Signal measurements
- `WS /ws/signal/` - WebSocket for GPS/signal streaming

## Using Real MeshCore Radio

1. **Plug in USB radio** to your laptop/Pi

2. **Find your radio** (easiest method):
   ```bash
   uv run python manage.py find_usb_radio
   ```

   This will:
   - List all USB serial devices
   - Highlight likely MeshCore radios
   - Show you the exact port to use

   Or manually find the port:
   ```bash
   # Mac
   ls /dev/tty.*

   # Linux
   ls /dev/ttyACM* /dev/ttyUSB*
   ```

3. **Update .env:**
   ```bash
   SERIAL_PORT=/dev/tty.usbmodem21401
   ```

   Or automatically update:
   ```bash
   uv run python manage.py find_usb_radio --update-env
   ```

4. **Test connection** (optional):
   ```bash
   uv run python manage.py find_usb_radio --test
   ```

5. **Restart server**

**Note:** The `meshcore` library integration uses `radio.getStats()` to read signal data. Adjust [max/radio_interface.py:109](max/radio_interface.py:109) if your MeshCore library has a different API.

## Related Projects

### MeshCore MQTT Broker
**Repository:** https://github.com/michaelhart/meshcore-mqtt-broker

**Important Note:** The main developer (Tree) runs the main meshcore-analyzer website. This MQTT broker project may have overlapping functionality with our analytics platform. We should coordinate with them as there may be opportunities to merge or integrate our projects in the future.

## Next Steps

- [ ] Fine-tune MeshCore radio API integration (verify getStats() method)
- [ ] Build Repeater Monitor frontend dashboard
- [ ] Deploy to Raspberry Pi with systemd services
- [ ] Add advanced heatmap interpolation
- [ ] Evaluate integration opportunities with meshcore-mqtt-broker

See full roadmap in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
