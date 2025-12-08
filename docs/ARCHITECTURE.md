# MeshCore Analytics - System Architecture

## Overview

An integrated Django/GeoDjango web application for monitoring and analyzing MeshCore mesh networks. The app runs on a Raspberry Pi and provides two complementary features:

1. **Repeater Monitor** - Real-time health monitoring and telemetry tracking of mesh network repeater nodes
2. **Signal Mapper** - Field survey tool for collecting and visualizing signal coverage heatmaps

The application is designed to run on a Raspberry Pi carried during field operations, combining USB-connected radio telemetry with phone-based GPS for comprehensive network analysis.

## Product Features

### Feature 1: Repeater Monitor

**Purpose:** Monitor the health, performance, and connectivity of MeshCore repeater nodes in real-time.

**Capabilities:**
- Track repeater battery voltage and power status
- Monitor signal quality (noise floor, RSSI, SNR)
- Analyze packet statistics (sent, received, duplicates, floods)
- View air time usage and uptime
- Visualize mesh topology (which nodes can hear each other)
- Alert on error events and connectivity issues

**Data Sources:**
- USB-connected MeshCore radio via serial port
- Periodic polling of repeater statistics
- Node contact list synchronization

**Current Status:**
- Backend models and API complete
- Django admin interface functional
- Frontend dashboard not yet implemented

### Feature 2: Signal Mapper

**Purpose:** Create signal coverage heatmaps for specific repeater nodes during field surveys.

**Capabilities:**
- Select target repeater to test
- Collect GPS coordinates + signal strength measurements
- Manual or continuous (interval-based) collection modes
- Real-time heatmap visualization with color-coded signal strength
- Session tracking for organized data collection
- Export coverage maps as GeoJSON

**Data Sources:**
- Phone GPS via browser Geolocation API
- MeshCore radio signal readings (RSSI/SNR)
- Combined by Pi and stored in PostGIS database

**Current Status:**
- Frontend web interface complete (Leaflet.js map)
- REST API for measurements functional
- WebSocket integration needed for Pi architecture

### Feature Integration

Both features share:
- **Node Registry** - Central database of all mesh network devices
- **Spatial Database** - PostGIS for location-aware queries
- **User Management** - Unified authentication and admin interface
- **REST API** - Common API structure for data access
- **Admin Interface** - Single control panel for all data

## Core Architecture

### Hardware Setup

```
┌─────────────────────────┐
│  Raspberry Pi           │
│  (in backpack)          │
├─────────────────────────┤
│ • MeshCore Radio (USB)  │ ← USB serial connection
│ • WiFi Client           │ ← Connects to phone's hotspot
│ • Django Server         │
│ • PostgreSQL + PostGIS  │
│ • Telemetry Service     │
└──────────┬──────────────┘
           │
           │ WiFi (phone's hotspot)
           │
     ┌─────▼──────┐
     │   Phone    │
     ├────────────┤
     │ • GPS      │ → Sends coordinates to Pi (Signal Mapper)
     │ • Cellular │ → Internet access
     │ • Browser  │ → Web interface at http://meshmap.local
     └────────────┘
```

### Network Configuration

- **Phone creates WiFi hotspot** (iOS Personal Hotspot or Android Hotspot)
- **Pi connects TO phone's WiFi hotspot** (not creating its own)
- Phone maintains cellular internet connection
- Pi accessible via mDNS at `http://meshmap.local`
- Phone browser accesses Django app on same WiFi network
- Phone sends GPS coordinates to Pi via WebSocket (Signal Mapper feature)

### Component Roles

#### Phone (iOS/Android Browser)
- **GPS Provider**: Streams real-time GPS coordinates via browser Geolocation API (Signal Mapper)
- **Internet Gateway**: Provides cellular data connection to Pi
- **User Interface**: Web browser displays both Repeater Monitor dashboard and Signal Mapper
- **WiFi Hotspot**: Creates network for Pi to connect to

#### Raspberry Pi (Backpack Unit)
- **Web Server**: Runs Django application accessible at `http://meshmap.local`
- **Radio Interface**: Reads telemetry and signal data from USB-connected MeshCore radio via serial
- **Data Processor**: Combines GPS stream from phone with radio signal data (Signal Mapper)
- **Data Logger**: Continuously collects repeater telemetry (Repeater Monitor)
- **Database**: PostgreSQL + PostGIS stores all measurements, stats, and spatial data
- **WiFi Client**: Connects to phone's hotspot for communication

#### MeshCore Radio (USB to Pi)
- Connected via USB serial port (e.g., `/dev/ttyACM0`)
- Provides RSSI (signal strength) and SNR (signal quality) measurements
- Reports repeater telemetry (battery, packets, uptime, neighbors)
- Continuously monitored by Pi background service

## Data Flow

### Repeater Monitor Flow

1. **Telemetry Collection** (Radio → Pi)
   - Pi serial service reads from USB port (`/dev/ttyACM0`)
   - Polls MeshCore radio for repeater statistics
   - Extracts battery voltage, signal metrics, packet counts, air time
   - Stores `RepeaterStats` records in database with timestamp

2. **Node Discovery** (Radio → Pi)
   - Management command loads contact list from radio
   - Creates/updates `Node` records with mesh_identity, public_key, role
   - Updates last_seen timestamps

3. **Neighbor Mapping** (Radio → Pi)
   - Reads which nodes each repeater can hear
   - Stores `NeighbourInfo` with SNR between node pairs
   - Enables mesh topology visualization

4. **Dashboard Display** (Pi → Phone)
   - REST API serves repeater stats and node information
   - Frontend dashboard shows real-time health metrics
   - Admin interface provides detailed data exploration

### Signal Mapper Flow

1. **GPS Streaming** (Phone → Pi)
   - Phone browser establishes WebSocket connection to Pi
   - Browser Geolocation API streams GPS coordinates
   - WebSocket sends GPS data to Pi in real-time

2. **Signal Monitoring** (Radio → Pi)
   - Pi reads from USB serial port (`/dev/ttyACM0`)
   - Background service polls MeshCore radio for current signal stats
   - Extracts RSSI, SNR for target repeater

3. **Data Combination** (Pi Processing)
   - Pi receives GPS from WebSocket
   - Pi reads signal data from radio
   - Combines GPS + signal into `SignalMeasurement`
   - Stores in PostGIS database with spatial indexing

4. **Visualization** (Pi → Phone)
   - User triggers heatmap generation via web interface
   - Pi queries measurements for selected node and session
   - Generates GeoJSON with signal strength data
   - Phone browser displays coverage heatmap with Leaflet.js
   - Color gradient: Blue (weak) → Red (strong)

### Measurement Data Structure

```json
{
  "location": {
    "type": "Point",
    "coordinates": [longitude, latitude]
  },
  "altitude": 123.4,
  "gps_accuracy": 5.2,
  "target_node": "node_id",
  "rssi": -78,
  "snr": 12.5,
  "session_id": "uuid",
  "timestamp": "2025-12-08T12:34:56Z"
}
```

## Technology Stack

### Backend (Raspberry Pi)

**Core Framework**
- Django 6.0 with GeoDjango
- PostgreSQL + PostGIS for spatial data
- Django Channels for WebSocket (real-time GPS + signal streaming)
- Django REST Framework + DRF-GIS for GeoJSON API

**Hardware Integration**
- `pyserial` - USB serial communication with MeshCore radio
- `meshcore` (v2.2) - MeshCore protocol library

**Spatial Processing**
- `scipy` - Signal interpolation for heatmaps
- `numpy` - Numerical processing
- PostGIS - Spatial queries and indexing

**Optional**
- Celery - Background heatmap generation
- Redis - WebSocket channel layer and caching

### Frontend (Phone Browser)

**Mapping & Visualization**
- Leaflet.js - Interactive map display
- Leaflet.heat - Heatmap rendering
- GeoJSON - Spatial data format

**Communication**
- WebSocket API - Real-time GPS streaming to Pi (Signal Mapper)
- Fetch API - REST API calls for data retrieval (both features)
- Geolocation API - GPS from phone (Signal Mapper)

**UI**
- Responsive HTML/CSS/JS (ES6 modules)
- Works on iOS Safari and Android Chrome
- No build step required
- Shared base template with navigation

### MeshCore Integration

**Current Implementation**
- Django management command: `python manage.py load_radio_data`
- Reads contacts from USB radio into Node database
- Uses `meshcore` Python library for serial communication

**Planned Implementation**
- Background systemd service for continuous telemetry collection
- Real-time signal data streaming via WebSocket
- Automatic node discovery and tracking
- Configurable polling intervals

## Network Protocols

### HTTP/HTTPS
- Web interface: `http://meshmap.local/`
- Repeater Monitor: `http://meshmap.local/monitor/` (planned)
- Signal Mapper: `http://meshmap.local/mapper/` (current: `/`)
- REST API: `http://meshmap.local/api/v1/`
- Django admin: `http://meshmap.local/admin/`

### WebSocket
- Signal/GPS stream: `ws://meshmap.local/ws/signal/`
- Real-time measurement updates
- Bidirectional communication (GPS → Pi, Signal → Phone)

### Serial (USB)
- Device: `/dev/ttyACM0` (or `/dev/ttyUSB0`)
- Baud rate: Determined by MeshCore radio
- Protocol: MeshCore binary protocol

### mDNS
- Hostname: `meshmap.local`
- Service: `_http._tcp` on port 8000 (or 80)
- Allows phone to discover Pi without knowing IP address

## Database Schema

### Core Models

**User** - Authentication and ownership
- Custom Django AbstractUser
- Associates data with collectors

**Node** - MeshCore mesh network devices (shared by both features)
- Spatial: `PointField(srid=4326)` for GPS location
- Fields: mesh_identity, public_key, name, role, firmware_version, is_active, is_favourite
- Roles: REPEATER (0), CLIENT (1), GATEWAY (2), SENSOR (3)
- Timestamps: first_seen, last_seen

**RepeaterStats** - Telemetry from repeaters (Repeater Monitor)
- Fields:
  - Power: batt_milli_volts
  - Signal: noise_floor, last_rssi, last_snr
  - Packets: n_packets_recv, n_packets_sent, n_recv_flood, n_recv_direct, etc.
  - Time: total_air_time_secs, total_rx_air_time_secs, total_up_time_secs
  - Errors: err_events
- Index: timestamp
- ForeignKey: node

**NeighbourInfo** - Mesh topology (Repeater Monitor)
- Fields: node, neighbour, snr
- Unique constraint: (node, neighbour)
- Enables mesh network visualization

**SignalMeasurement** - Coverage heatmap data points (Signal Mapper)
- Spatial: `PointField(srid=4326)` for collection location
- Fields: location, altitude, gps_accuracy, rssi, snr, target_node, session_id, collector_user
- Indexes: (target_node, timestamp), session_id

### Spatial Indexing
- All spatial fields use SRID 4326 (WGS84 standard GPS)
- PostGIS GiST indexes for fast spatial queries
- Supports radius searches, bounding box queries, nearest neighbor

## Application Structure

### URL Routing
```
/                          → Landing page / Dashboard
/monitor/                  → Repeater Monitor (planned)
/mapper/                   → Signal Mapper (current: /)
/admin/                    → Django admin interface
/api/v1/nodes/            → Node list (GET)
/api/v1/measurements/     → Signal measurements (GET/POST)
/api/v1/repeater-stats/   → Repeater telemetry (planned)
/ws/signal/               → WebSocket for GPS/signal streaming
```

### Django Apps Structure

**Current:** Single `max` app contains all features
**Recommended Future:** Organize into separate apps
```
meshcore-analytics/
├── core/              # Shared models (User, Node)
├── repeater_monitor/  # RepeaterStats, NeighbourInfo, telemetry views
├── signal_mapper/     # SignalMeasurement, collection views
└── api/              # REST API for both features
```

## Deployment Configuration

### Pi Requirements
- Raspberry Pi 3/4/Zero 2 W (WiFi required)
- Python 3.14+
- PostgreSQL 14+ with PostGIS extension
- Avahi daemon for mDNS (`avahi-daemon`)
- USB port for MeshCore radio
- 16GB+ SD card recommended

### Network Setup
1. Configure Pi WiFi to connect to phone's hotspot (store credentials in `/etc/wpa_supplicant/wpa_supplicant.conf`)
2. Install Avahi and configure hostname: `meshmap.local`
3. Start Django server on boot via systemd
4. Start background telemetry service via systemd

### Environment Variables
```bash
DJANGO_SETTINGS_MODULE=max.settings
DATABASE_URL=postgis://postgres:password@localhost/meshcore_analytics
ALLOWED_HOSTS=meshmap.local,*.local,192.168.*.*
DEBUG=False
SECRET_KEY=<secure-random-key>
SERIAL_PORT=/dev/ttyACM0
```

### Systemd Services
- `meshcore-web.service` - Django/Daphne server (both features)
- `meshcore-telemetry.service` - Background repeater telemetry collection
- `postgresql.service` - Database server

## Security Considerations

### Network
- Local network only (WiFi hotspot)
- No external internet exposure by default
- Optional: Basic auth for admin interface
- CSRF protection enabled for API

### Data
- Optional user authentication
- Anonymous measurement collection supported
- Session IDs for grouping measurements
- No sensitive data transmitted

## Development Workflow

### Local Development (Mac/Linux)
```bash
# Start PostgreSQL with PostGIS
# Configure database in settings.py

# Run migrations
python manage.py migrate

# Load radio contacts (if radio connected)
python manage.py load_radio_data

# Start development server
python manage.py runserver

# Access at http://localhost:8000
```

### Pi Deployment
```bash
# Install dependencies
sudo apt-get install postgresql postgis avahi-daemon python3-pip

# Install Python packages
pip install -r requirements.txt

# Configure systemd services
sudo systemctl enable meshcore-web
sudo systemctl enable meshcore-telemetry

# Start services
sudo systemctl start meshcore-web
sudo systemctl start meshcore-telemetry
```

## Future Enhancements

### Repeater Monitor
- [ ] Real-time dashboard with live telemetry charts
- [ ] Historical trend analysis and graphing
- [ ] Alerting system for low battery or connectivity issues
- [ ] Mesh topology visualization with network graph
- [ ] Repeater performance comparison tools

### Signal Mapper
- [ ] Real-time heatmap updates during collection
- [ ] Offline capability with sync when connected
- [ ] Multiple simultaneous target node monitoring
- [ ] Export measurements as GeoJSON/KML/CSV
- [ ] Advanced interpolation algorithms (kriging, IDW)
- [ ] 3D signal propagation visualization

### Shared Infrastructure
- [ ] Progressive Web App (PWA) for offline UI
- [ ] Power management and battery monitoring
- [ ] Automatic backup to cloud when internet available
- [ ] Multi-radio support (multiple USB radios)
- [ ] Remote access via VPN or cloud tunnel
- [ ] Mobile app (native iOS/Android)

## OSS Project Goals

This is designed as an open-source project for the MeshCore community with the following principles:

- **Single Device Deployment** - Everything runs on one Pi, easy to set up and carry
- **Field-Ready** - Designed for outdoor surveys and real-world mesh network analysis
- **Community Data** - Enable coverage mapping and repeater health monitoring for mesh networks
- **Educational** - Help users understand mesh network performance and signal propagation
- **Extensible** - Plugin architecture for additional analysis tools and visualizations
