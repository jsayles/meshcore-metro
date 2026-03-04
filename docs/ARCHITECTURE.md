# MeshCore Analytics - System Architecture

## Overview

An integrated Django/GeoDjango web application for monitoring and analyzing MeshCore mesh networks. The app runs on a Raspberry Pi and provides four complementary features:

1. **Mesh Configuration** - Discover and manage repeater contacts from your radio
2. **Repeater Monitor** - Real-time health monitoring and telemetry tracking of mesh network repeater nodes
3. **Field Testing** - Field survey tool for collecting and visualizing signal coverage heatmaps
4. **WiFi Hotspot Configuration** - Configure Pi's connection to phone's WiFi hotspot

The application is designed to run on a Raspberry Pi carried during field operations, combining USB-connected radio telemetry with phone-based GPS for comprehensive network analysis.

## Product Features

### Feature 1: Mesh Configuration

**Purpose:** Discover and manage which repeater contacts are tracked in the local database.

**Capabilities:**
- Auto-discover repeater contacts from connected radio on page load
- View "My Repeaters" (nodes already in database)
- Browse "Add Repeaters" list (discovered nodes not yet in database)
- Add repeaters to database with single click
- Remove repeaters from database
- Search/filter discovered repeaters
- Pagination for large contact lists (50 per page)
- Client-side favorites/starring for sorting (transient, not saved)

**Data Sources:**
- USB-connected MeshCore radio contacts via `mc.ensure_contacts()`
- Filters to show only repeaters (type=2) from radio
- API filters out nodes already in database

**Current Status:**
- ✅ Frontend UI complete with two-section layout
- ✅ REST API endpoints functional (discover, add, delete)
- ✅ Auto-redirect from home if no repeaters configured
- ✅ Navbar with gear icon for configuration access
- ✅ Search and pagination implemented

**Workflow:**
1. First-time users redirected to `/config/mesh/` automatically
2. Page loads existing repeaters from database (top section)
3. Auto-discovers available repeaters from radio (bottom section)
4. User clicks star icon and "Add to Mesh" to add repeaters
5. Remove button available for nodes in database
6. Run `load_radio_data` command to update telemetry for tracked nodes

### Feature 2: Repeater Monitor

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

### Feature 3: Field Testing

**Purpose:** Create signal coverage heatmaps for specific repeater nodes during field surveys.

**Capabilities:**
- Select target repeater to test (via dropdown or URL parameter)
- Collect GPS coordinates + signal strength measurements
- Manual or continuous (interval-based) collection modes
- Real-time heatmap visualization with color-coded signal strength
- Field test-based measurement tracking (Django FieldTest model)
- Responsive sidebar interface (420px width)
- Mobile-friendly with automatic GPS streaming
- Automatic heatmap updates after each measurement
- Map centered on Vancouver, BC by default

**Data Sources:**
- Phone GPS via browser Geolocation API
- MeshCore radio signal readings (RSSI/SNR)
- Combined by Pi and stored in PostGIS database

**Current Status:**
- ✅ Frontend web interface complete (Leaflet.js map)
- ✅ REST API for measurements functional
- ✅ WebSocket integration complete for GPS streaming
- ✅ Field test-based tracking with Django FieldTest model
- ✅ 3-step setup workflow with progress indicators
- ✅ Responsive design for mobile devices

### Feature 4: WiFi Hotspot Configuration

**Purpose:** Configure and manage the Raspberry Pi's connection to a phone's WiFi hotspot.

**Capabilities:**
- Save WiFi hotspot SSID and password to database
- Scan for available WiFi networks (Linux only)
- Connect to configured hotspot
- View current connection status
- Platform-specific implementations (Linux with NetworkManager, macOS database-only)

**Implementation:**
- Platform abstraction via `wifi_hotspot.py` subsystem
- Linux: Full NetworkManager/nmcli integration for scanning, configuring, and connecting
- macOS: Database storage only (for development), manual connection required
- Configuration stored in `HotspotConfig` model (singleton pattern)
- Auto-connects on boot via NetworkManager connection profile

**Current Status:**
- ✅ WiFi hotspot subsystem with platform detection
- ✅ REST API endpoints (`/api/v1/hotspot/config/`, `/scan/`, `/configure/`, `/connect/`, `/capabilities/`)
- ✅ Frontend UI at `/config/hotspot/`
- ✅ Network scanning with signal strength display (Linux)
- ✅ Connection status monitoring
- ✅ Navbar submenu for Mesh/Hotspot configuration tabs

**Workflow:**
1. User navigates to `/config/hotspot/`
2. (Optional) Click "Scan Networks" to discover available WiFi networks
3. Select network from dropdown or enter SSID manually
4. Enter WiFi password
5. Click "Save Configuration" to store credentials and create NetworkManager profile
6. Click "Connect Now" to establish connection (or Pi auto-connects on next boot)

### Feature Integration

All features share:
- **Node Registry** - Central database of mesh network devices
- **Radio Interface** - USB serial connection to MeshCore radio
- **Spatial Database** - PostGIS for location-aware queries
- **WiFi Management** - Unified hotspot configuration system
- **User Management** - Unified authentication and admin interface
- **REST API** - Common API structure for data access
- **Admin Interface** - Single control panel for all data
- **Configuration UI** - Tabbed interface for Mesh and Hotspot settings

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
     │ • GPS      │ → Sends coordinates to Pi (Field Testing)
     │ • Cellular │ → Internet access
     │ • Browser  │ → Web interface at https://<hostname>.local:8443
     └────────────┘
```

### Network Configuration

- **Phone creates WiFi hotspot** (iOS Personal Hotspot or Android Hotspot)
- **Pi connects TO phone's WiFi hotspot** (not creating its own)
  - Configured via `/config/hotspot/` web interface
  - Credentials stored in database and NetworkManager (Linux)
  - Auto-connects on boot via NetworkManager connection profile
- Phone maintains cellular internet connection
- Pi accessible via mDNS at `https://<hostname>.local:8443` (HTTPS required for GPS)
- Phone browser accesses Django app on same WiFi network
- Phone sends GPS coordinates to Pi via secure WebSocket (Field Testing feature)
- Self-signed SSL certificate generated during installation

### Component Roles

#### Phone (iOS/Android Browser)
- **GPS Provider**: Streams real-time GPS coordinates via browser Geolocation API (Field Test)
- **Internet Gateway**: Provides cellular data connection to Pi
- **User Interface**: Web browser displays both Repeater Monitor dashboard and Field Test
- **WiFi Hotspot**: Creates network for Pi to connect to

#### Raspberry Pi (Backpack Unit)
- **Web Server**: Runs Django/Daphne application with HTTPS at `https://<hostname>.local:8443`
- **Radio Interface**: Reads telemetry and signal data from USB-connected MeshCore radio via serial
- **Data Processor**: Combines GPS stream from phone with radio signal data (Field Testing)
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

2. **Node Discovery** (Radio → Pi → Database)
   - Mesh Configuration UI discovers contacts from radio via API
   - User manually selects which repeaters to add to database
   - `load_radio_data` command updates existing nodes only (does not add new ones)
   - Updates name, location, role, last_seen for tracked nodes

3. **Neighbor Mapping** (Radio → Pi)
   - Reads which nodes each repeater can hear
   - Stores `NeighbourInfo` with SNR between node pairs
   - Enables mesh topology visualization

4. **Dashboard Display** (Pi → Phone)
   - REST API serves repeater stats and node information
   - Frontend dashboard shows real-time health metrics
   - Admin interface provides detailed data exploration

### Field Testing Flow

**3-Step Setup Process:**

1. **Step 1: Repeater Selection**
   - User navigates to `/mapper/?node=<id>` (pre-selected) or `/mapper/` (manual selection)
   - API fetches active repeater nodes: `GET /api/v1/nodes/?role=0&is_active=true`
   - If pre-selected via URL, shows repeater name in status
   - If manual, shows dropdown to select from available repeaters
   - Page redirects to URL with node parameter when repeater selected
   - Step marked complete when repeater chosen

2. **Step 2: Location Tracking**
   - Browser automatically requests GPS permission on page load
   - Geolocation API centers map on user's current location
   - Step marked complete with "Enabled" status
   - Falls back to Vancouver, BC center if permission denied

3. **Step 3: Companion Radio**
   - User clicks "Connect" button to establish WebSocket connection
   - WebSocket connects to `ws://[host]/ws/signal/`
   - Connection includes Django session ID for measurement tracking
   - GPS streaming begins automatically on successful connection
   - Step marked complete with "Connected" status
   - All steps lose active highlighting when complete

**Collection Process:**

4. **Measurement Collection** (appears after setup complete)
   - **Manual Mode**: Single measurement on button click
   - **Continuous Mode**: Interval-based collection (configurable seconds)
   - Each collection triggers:
     - GPS coordinates retrieved from browser
     - WebSocket sends GPS + collection request to Pi
     - Pi reads current signal data from USB radio (RSSI/SNR)
     - Pi combines GPS + signal → `SignalMeasurement` in database
     - API returns measurement count and last readings
     - Client updates stats display

5. **Automatic Heatmap Updates**
   - After each measurement, client fetches updated data
   - API query: `GET /api/v1/measurements/?target_node=<id>&session=<session_id>`
   - Client renders heatmap using Leaflet.heat plugin
   - Color gradient: Blue (weak signal) → Red (strong signal)
   - Map updates in real-time as measurements are collected

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
  "session_id": "django_session_key",
  "timestamp": "2025-12-08T12:34:56Z"
}
```

**Session Tracking:**
- Session IDs are generated server-side using Django's session framework
- Each browser session gets a unique session key
- All measurements in a field survey are grouped by session ID
- Enables viewing/replaying specific survey sessions

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
- WebSocket API - Real-time GPS streaming to Pi (Field Test)
- Fetch API - REST API calls for data retrieval (both features)
- Geolocation API - GPS from phone (Field Test)

**UI**
- Responsive HTML/CSS/JS (ES6 modules)
- Works on iOS Safari and Android Chrome
- No build step required
- Shared base template with navigation
- 420px responsive sidebar for controls
- Mobile-optimized with viewport settings
- Progress indicators with 3-step checklist
- Real-time status updates and messaging

### MeshCore Integration

**Radio Contact Types**
- Type 1: Client (companion radio/phone app)
- Type 2: Repeater (infrastructure nodes)
- Type 3: Room Server (BBS/message board nodes)

**Current Implementation**
- Mesh Configuration page: Discover and add repeaters via web UI at `/config/`
- Management command: `python manage.py load_radio_data` - Updates existing nodes only
- Uses `meshcore` Python library (v2.2.3) for serial communication
- Radio accessed via `/dev/cu.usbmodem*` or `/dev/ttyACM0`

**Planned Implementation**
- Background systemd service for continuous telemetry collection
- Real-time signal data streaming via WebSocket
- Configurable polling intervals

## Network Protocols

### HTTPS (Required for GPS/Positioning)
- Web interface: `https://<hostname>.local:8443/`
- Field Testing: `https://<hostname>.local:8443/field-testing/` or `https://<hostname>.local:8443/field-testing/?node=<id>`
- Repeater Monitor: `https://<hostname>.local:8443/monitor/` (planned)
- REST API: `https://<hostname>.local:8443/api/v1/`
  - Nodes: `GET /api/v1/nodes/?role=0&is_active=true`
  - Measurements: `GET/POST /api/v1/measurements/`
- Django admin: `https://<hostname>.local:8443/admin/`

**Note:** HTTPS is required because browsers only allow Geolocation API access over secure connections. The installation script generates a self-signed SSL certificate. Users must accept the browser security warning on first visit.

### Secure WebSocket
- Signal/GPS stream: `wss://<hostname>.local:8443/ws/signal/`
- Real-time measurement updates
- Bidirectional communication (GPS → Pi, Signal → Phone)
- Uses same SSL certificate as HTTPS server

### Serial (USB)
- Device: `/dev/ttyACM0` (or `/dev/ttyUSB0`)
- Baud rate: Determined by MeshCore radio
- Protocol: MeshCore binary protocol

### mDNS
- Hostname: `<hostname>.local` (where hostname is the Pi's configured hostname)
- Service: `_https._tcp` on port 8443
- Allows phone to discover Pi without knowing IP address
- Automatically configured by Avahi daemon (installed during setup)

## Database Schema

### Core Models

**User** - Authentication and ownership
- Custom Django AbstractUser
- Associates data with collectors

**Node** - MeshCore mesh network devices (shared by both features)
- Spatial: `PointField(srid=4326)` for GPS location
- Fields: mesh_identity, public_key, name, role, firmware_version, is_active
- Roles: REPEATER (0), CLIENT (1)
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

**Trace** - Coverage heatmap data points (Field Testing)
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
/                              → Mesh network home (redirects to /config/mesh/ if no repeaters)
/config/                       → Redirects to /config/mesh/
/config/mesh/                  → Mesh Configuration (discover and manage repeaters)
/config/hotspot/               → WiFi Hotspot Configuration
/field-testing/                → Field Testing (can include ?node=<id> parameter)
/monitor/                      → Repeater Monitor (planned)
/nodes/<id>/                   → Node detail view
/admin/                        → Django admin interface
/api/v1/nodes/                → Node list (GET) with filtering
/api/v1/nodes/discover/       → Discover repeaters from radio (POST)
/api/v1/nodes/add_node/       → Add discovered node to database (POST)
/api/v1/nodes/<id>/           → Delete node (DELETE)
/api/v1/field-tests/          → Field test CRUD operations
/api/v1/traces/               → Trace measurements (GET/POST)
/api/v1/repeater-stats/       → Repeater telemetry (planned)
/api/v1/hotspot/config/       → Get current hotspot config (GET)
/api/v1/hotspot/capabilities/ → Check platform WiFi capabilities (GET)
/api/v1/hotspot/scan/         → Scan for WiFi networks (POST, Linux only)
/api/v1/hotspot/configure/    → Save hotspot credentials (POST)
/api/v1/hotspot/connect/      → Connect to configured hotspot (POST)
/api/v1/hotspot/status/       → Check connection status (GET)
/ws/signal/                   → WebSocket for GPS/signal streaming
```

### Django Apps Structure

**Current:** Two apps with separation of concerns
```
meshcore-metro/
├── metro/                     # Main Django app
│   ├── models.py             # Core models (Node, FieldTest, Trace, HotspotConfig)
│   ├── views.py              # Web views (home, config pages, field testing)
│   ├── admin.py              # Django admin configuration
│   ├── subsystems/           # Platform-specific subsystems
│   │   └── wifi_hotspot.py   # WiFi management with Linux/macOS implementations
│   └── templates/metro/      # HTML templates
└── api/                      # REST API app
    ├── views.py              # API ViewSets (NodeViewSet, HotspotViewSet, etc.)
    ├── serializers.py        # DRF serializers
    └── urls.py               # API URL routing
```

**Recommended Future:** Further organize into feature-based apps
```
meshcore-metro/
├── core/              # Shared models (User, Node)
├── mesh_config/       # Node discovery and management UI
├── wifi_config/       # WiFi hotspot configuration and subsystems
├── repeater_monitor/  # RepeaterStats, NeighbourInfo, telemetry views
├── field_testing/     # FieldTest, Trace models and views
└── api/              # REST API for all features
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
1. **WiFi Configuration**: During installation, script prompts for phone hotspot credentials
   - Credentials stored in `/etc/wpa_supplicant/wpa_supplicant.conf`
   - Pi auto-connects to phone hotspot on boot
   - Falls back to any other known networks if hotspot unavailable
2. **mDNS Setup**: Avahi daemon installed and enabled
   - Pi accessible at `https://<hostname>.local:8443`
   - Hostname determined from Pi's system hostname (no configuration needed)
3. **SSL Certificates**: Self-signed certificate generated for HTTPS
   - Required for browser Geolocation API access
   - Valid for hostname.local, hostname, localhost, and 127.0.0.1
4. **Services**: Optional systemd services for production deployment
   - `meshcore-web.service` - Django/Daphne server
   - `meshcore-telemetry.service` - Background repeater telemetry collection

### Environment Variables
```bash
DJANGO_SETTINGS_MODULE=metro.settings
DATABASE_URL=postgis://postgres:password@localhost/metrodb
ALLOWED_HOSTS=*
DEBUG=False
SECRET_KEY=<secure-random-key>
SERIAL_PORT=/dev/ttyACM0
```

**Notes:**
- `ALLOWED_HOSTS=*` allows any hostname, making the Pi accessible regardless of hostname configuration
- `SECRET_KEY` is used for both Django session/CSRF security and field encryption (via SHA-256 derivation)
- The encryption key for `django-encrypted-model-fields` is automatically derived from `SECRET_KEY` using SHA-256

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

### Encryption
- WiFi passwords stored encrypted using `django-encrypted-model-fields`
- Encryption key derived from `SECRET_KEY` using SHA-256 hash
- Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256)
- Password never exposed in API responses (write-only field)
- Ensure `SECRET_KEY` is properly secured in production

**Important:** WiFi passwords briefly appear in system process lists during configuration due to NetworkManager CLI limitations. This is standard behavior for `nmcli` commands and passwords are quickly removed from memory once the connection profile is created.

## Development Workflow

### Local Development (Mac/Linux)
```bash
# Start PostgreSQL with PostGIS
# Configure database in settings.py

# Run migrations
python manage.py migrate

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

### Field Testing
- [x] 3-step setup workflow with progress indicators
- [x] Session-based measurement tracking
- [x] Real-time heatmap updates during collection
- [x] Mobile-friendly responsive interface
- [x] WebSocket GPS streaming
- [x] Manual and continuous collection modes
- [ ] Offline capability with sync when connected
- [ ] Multiple simultaneous target node monitoring
- [ ] Export measurements as GeoJSON/KML/CSV
- [ ] Advanced interpolation algorithms (kriging, IDW)
- [ ] 3D signal propagation visualization
- [ ] Historical session playback and comparison

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
