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
- MeshCore radio (optional - uses mock data if not connected)

### Setup

```bash
# 1. Install dependencies
uv sync

# 2. Create database
createdb meshcore_analytics
psql meshcore_analytics -c "CREATE EXTENSION postgis;"

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

# Set to False to use real radio, True for mock data
USE_MOCK_RADIO=False
```

```bash
# 4. Run migrations
uv run python manage.py migrate

# 5. Create test node (optional)
uv run python manage.py shell
```

In shell:
```python
from max.models import Node
from django.contrib.gis.geos import Point

Node.objects.create(
    name="Test Repeater 1",
    mesh_identity="TEST_001",
    role=0,  # REPEATER
    location=Point(-122.4194, 37.7749, srid=4326),
    is_active=True
)
```

### Running Signal Mapper

**Terminal 1 - Redis:**
```bash
redis-server
```

**Terminal 2 - Django with Channels:**
```bash
uv run daphne -b 0.0.0.0 -p 8000 max.asgi:application
```

**Browser:**
- Signal Mapper: http://localhost:8000/
- Admin: http://localhost:8000/admin/
- API: http://localhost:8000/api/v1/

## Signal Mapper Workflow

1. Open http://localhost:8000/ in browser
2. Click "Connect to Pi" → WebSocket established, GPS streaming starts
3. Select target repeater from dropdown
4. Click "Collect Now" to capture measurement (mock RSSI/SNR)
5. Repeat at different locations
6. Click "Load Heatmap" to visualize coverage

**Mode Selection:**
- **Mock Mode** (`USE_MOCK_RADIO=True`): Uses random signal values for testing
- **Real Mode** (`USE_MOCK_RADIO=False`): Reads actual signal data from USB-connected MeshCore radio

The system automatically falls back to mock mode if the radio isn't connected or libraries are missing.

## Development Commands

```bash
# Run with Channels/WebSocket support (REQUIRED for Signal Mapper)
uv run daphne -b 0.0.0.0 -p 8000 max.asgi:application

# Traditional Django (no WebSocket - Signal Mapper won't work, but admin/API will)
uv run python manage.py runserver

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
│   ├── radio_interface.py  # USB radio interface (mock mode)
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
   SERIAL_PORT=/dev/tty.usbmodem21401  # Your device
   USE_MOCK_RADIO=False
   ```

   Or automatically update:
   ```bash
   uv run python manage.py find_usb_radio --update-env
   ```

4. **Test connection** (optional):
   ```bash
   uv run python manage.py find_usb_radio --test
   ```

5. **Restart server** - it will now read real RSSI/SNR from the radio!

**Note:** The `meshcore` library integration uses `radio.getStats()` to read signal data. Adjust [max/radio_interface.py:109](max/radio_interface.py:109) if your MeshCore library has a different API.

## Next Steps

- [ ] Fine-tune MeshCore radio API integration (verify getStats() method)
- [ ] Build Repeater Monitor frontend dashboard
- [ ] Deploy to Raspberry Pi with systemd services
- [ ] Add advanced heatmap interpolation

See full roadmap in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
