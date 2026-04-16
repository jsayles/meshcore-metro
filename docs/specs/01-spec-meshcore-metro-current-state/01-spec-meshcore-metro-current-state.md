# 01-spec-meshcore-metro-current-state

## Introduction/Overview

MeshCore METRO is a Django/GeoDjango web application for monitoring a MeshCore LoRa mesh repeater network. It runs on a Raspberry Pi connected via USB to a MeshCore radio, and is accessed through a phone browser over WiFi. The application allows an operator to discover repeaters from the radio, track their status on a map, ping them to confirm reachability, and configure routing paths.

This spec documents the current state of the application as the foundation for future feature development.

## Goals

- Provide a single source of truth for what MeshCore METRO currently does — its models, views, API endpoints, and business rules
- Serve as accurate acceptance criteria for regression testing existing behavior
- Act as the baseline spec from which future feature specs (monitoring dashboard, telemetry collection, neighbor topology) can branch

## User Stories

**As a network operator**, I want to discover repeaters reachable by my radio so that I can add them to my monitored network.

**As a network operator**, I want to see all known repeaters on a map with freshness indicators so that I can quickly assess the state of the network.

**As a network operator**, I want to ping a specific repeater and see its SNR values so that I can verify it is reachable and measure link quality.

**As a network operator**, I want to configure how a node is routed (flood, direct, or multi-hop) so that I can control how trace commands reach it.

**As a network operator**, I want to run a management command to sync node data from the radio so that existing records stay current without manual entry.

## Demoable Units of Work

### Unit 1: Repeater Discovery and Database Management

**Purpose:** Allows the operator to find repeaters the radio can hear and add them to the application's database for ongoing tracking.

**Functional Requirements:**
- The system shall provide a `/config/mesh/` page showing two sections: "My Repeaters" (nodes in the database) and "Add Repeaters" (discovered nodes not yet in the database).
- The system shall POST to `/api/v1/nodes/discover/` to connect to the USB radio and return a list of repeater contacts (type == 2), excluding those already in the database, as a transient JSON payload.
- The system shall filter, search, and sort the discovered list client-side by name/mesh_identity with real-time filtering and pagination (50 per page).
- The system shall allow the operator to POST to `/api/v1/nodes/add_node/` with a discovered node's data to create a Node record in the database; if a node with that `mesh_identity` already exists, the request shall return an error.
- The system shall allow the operator to DELETE `/api/v1/nodes/{id}/` to remove a node from the database.
- The system shall redirect `/config/` to `/config/mesh/`.
- The system shall redirect the home page to `/config/mesh/` when no repeater nodes exist in the database.

**Proof Artifacts:**
- Browser screenshot: `/config/mesh/` showing "My Repeaters" list and "Add Repeaters" table with at least one discovered entry demonstrates end-to-end discovery flow
- API response: POST `/api/v1/nodes/discover/` returns `{ "count": N, "nodes": [...] }` demonstrates radio integration
- API response: POST `/api/v1/nodes/add_node/` returns GeoJSON Feature with node properties demonstrates persistence

---

### Unit 2: Network Overview Map

**Purpose:** Gives the operator a geographic view of all known repeaters with freshness-based status indicators.

**Functional Requirements:**
- The system shall render a full-screen Leaflet map at `/` showing all active repeaters (role=0, is_active=true) fetched from `/api/v1/nodes/?is_active=true&role=0`.
- The system shall color each node marker based on `last_seen` age: green (< 24 hours), yellow (< 1 week), red (> 1 week).
- The system shall display a floating info panel (top-right) showing total repeater count and a list of up to 10 current nodes (< 24h), sorted by most-recently-seen.
- The system shall show a popup on marker click with: node name, status badge, coverage range, last seen timestamp, and a "View Details" link.
- Clicking a repeater name in the sidebar shall zoom the map to that node and open its popup.
- The system shall auto-fit the map bounds to show all nodes on initial load.

**Proof Artifacts:**
- Browser screenshot: `/` with nodes rendered on the map, color-coded and with sidebar visible demonstrates overview functionality
- Network request: GET `/api/v1/nodes/?is_active=true&role=0` returns GeoJSON FeatureCollection demonstrates API contract

---

### Unit 3: Node Detail, Ping, and Route Configuration

**Purpose:** Provides per-node inspection, reachability testing, and routing control.

**Functional Requirements:**
- The system shall render a detail page at `/node/<id>/` showing: node type, active/inactive status, mesh identity, firmware version, coverage range, first seen, last seen, and description.
- The system shall display a Leaflet map centered on the node's location (if set), with a circle overlay representing `estimated_range` and an emoji marker (📡 or 📱).
- The system shall display the node's coordinates and altitude if available.
- The system shall provide a "Ping" button that POSTs to `/api/v1/nodes/{id}/ping/`, which connects to the radio, sends a trace command using the node's `path` for routing, and returns `{ "reachable": bool, "snr_to_target": float, "snr_from_target": float, "latency_ms": int }` on success or `{ "reachable": false, "error": string }` on failure.
- The ping result shall be displayed with color-coded feedback: green for reachable, red for no response, yellow for radio error.
- A successful ping shall update the node's `last_seen` timestamp.
- The system shall provide a route configuration UI with three radio-button options:
  - **Flood** — sets `path` to blank (broadcasts mesh-wide)
  - **Direct** — sets `path` to the first 2 characters of `mesh_identity` (1-byte hash)
  - **Fixed Path** — sets `path` to a user-provided comma-separated hex hash string (supports 2-, 4-, and 6-character hash segments)
- Changing the route selection shall enable a "Save" button; clicking it shall PATCH `/api/v1/nodes/{id}/` with the new `path` value.

**Proof Artifacts:**
- Browser screenshot: `/node/<id>/` with map, info card, ping result, and route selector visible demonstrates the full detail view
- API response: POST `/api/v1/nodes/{id}/ping/` returning `{ "reachable": true, "snr_to_target": ..., "snr_from_target": ..., "latency_ms": ... }` demonstrates radio round-trip
- API response: PATCH `/api/v1/nodes/{id}/` with updated `path` demonstrates route persistence

---

### Unit 4: Radio Interface and Management Commands

**Purpose:** Provides the low-level USB serial communication layer and CLI tools for radio setup and data loading.

**Functional Requirements:**
- The `RadioInterface` class (`metro/subsystems/lora_radio.py`) shall connect to a MeshCore radio via USB serial at the configured port and baud rate, and support use as an async context manager.
- `RadioInterface.discover_nodes(timeout)` shall return a list of repeater contacts from `mc.ensure_contacts()`, each with `pubkey`, `mesh_identity`, `node_type`, `name`, `snr`, `rssi`, `path_len`, and optionally `lat`/`lon` (when `adv_lat`/`adv_lon` are non-zero).
- `RadioInterface.get_current_signal(node)` shall send a trace command using `node.path` for routing and return `{ "snr_to_target": float, "snr_from_target": float }` from the TRACE_DATA event, with a 10-second timeout returning `None` on no response.
- The `find_usb_radio` management command shall list all detected USB serial ports, mark likely MeshCore candidates (Espressif, CP210x, CH340, FTDI, USB JTAG), and optionally write the first candidate to `.env` via `--save`.
- The `load_radio_data` management command shall fetch all contacts from the radio and update matching Node records (by `mesh_identity`) with fresh `name`, `public_key`, `role`, `last_seen`, and location (if non-zero lat/lon advertised). It shall skip contacts not already in the database.

**Proof Artifacts:**
- CLI output: `python manage.py find_usb_radio` listing detected ports with ✓ marks demonstrates hardware discovery
- CLI output: `python manage.py load_radio_data` showing "Updated: <node name>" lines demonstrates contact sync
- Unit test or manual trace: `RadioInterface.get_current_signal()` returning SNR values demonstrates serial protocol integration

## Non-Goals (Out of Scope)

1. **Real-time telemetry polling**: `RepeaterStats` model schema exists (battery voltage, RSSI, SNR, packet counts, uptime) and is registered in admin, but no background poller currently writes to it. This is planned for a future monitoring feature.
2. **Neighbour topology tracking**: `NeighbourInfo` model schema exists (node, neighbour, SNR, timestamps) but no code currently populates it. Planned for a future topology/graph feature.
3. **WebSocket monitoring dashboard**: `MonitoringConsumer` is wired up and accepts connections to the `"monitoring"` group, but has no message handlers. The infrastructure (Channels + Redis) is in place; the feature is planned.
4. **WiFi hotspot configuration**: Removed from scope. The app's focus shifted to network monitoring only, which does not require configuring the Pi's WiFi hotspot.
5. **Field testing / signal heatmaps**: Removed from scope alongside the hotspot feature. Not present in the codebase.
6. **Background polling interval**: `MESHCORE_POLL_INTERVAL` is defined in settings but nothing currently reads it. Will be used when telemetry polling is implemented.
7. **Client node management**: The Node model supports `role=CLIENT` but discovery, configuration, and the overview map filter to `role=REPEATER` only.

## Design Considerations

**Navigation:**
- Base template provides a dark navbar (`#2c3e50`) with links to Home (`/`) and Configuration (`/config/mesh/`). Active link is highlighted in `#3498db`.
- Status messages appear in a fixed top-right overlay with auto-dismiss after 5 seconds.

**Map:**
- All map views use Leaflet.js with OpenStreetMap tiles.
- Coverage areas are rendered as circles with radius = `estimated_range` (meters).
- Node freshness uses three colors: green < 24h, yellow < 1 week, red > 1 week.

**Responsive:**
- Node detail page uses a two-column grid on desktop, stacked on mobile.
- Status messages shift to bottom-fixed on mobile.
- Buttons go full-width on mobile.

**CSS Variables (defined in `metro.css`):**
- `--primary-color`, `--success-color`, `--danger-color`, `--secondary-color`, `--bg-color`, `--text-color`, `--border-color`, `--inactive-color`

## Repository Standards

- **Dependency management**: `uv` with `pyproject.toml`
- **Django version**: 6.0; Python 3.14+
- **Database**: PostgreSQL + PostGIS via `django.contrib.gis.db.backends.postgis`
- **ASGI server**: Daphne (not gunicorn/uwsgi)
- **API**: Django REST Framework + DRF-GIS (`GeoFeatureModelSerializer`); all node responses are GeoJSON Features
- **Frontend**: Vanilla ES6 modules, no framework. JS classes per page (`NodeOverview`, `MeshConfig`).
- **CSS**: Variables for all colors — no hardcoded hex values in stylesheets
- **Environment config**: `.env` file loaded via `python-dotenv`; secrets never committed
- **Static files**: WhiteNoise for serving; `STATIC_ROOT = BASE_DIR/staticfiles`
- **Migrations**: Standard Django migrations; PostGIS extension must exist before first migrate

## Technical Considerations

**Radio Communication:**
- All radio operations are async (Python asyncio). API views run them via `asyncio.run()` or event-loop bridging.
- Serial port and baud rate come from `settings.MESHCORE_SERIAL_PORT` and `settings.MESHCORE_BAUD_RATE` (defaults: `/dev/ttyACM0`, 115200).
- The `meshcore` library (v2.2.x) handles the MeshCore protocol. `mc.ensure_contacts()` is the primary discovery call.
- `send_trace(path=...)` drives both ping and signal measurement. `path=None`/blank → flood; `"XX"` → direct (2-char = 1-byte hash); comma-separated → multi-hop. The library also supports 4-char (2-byte) and 6-char (3-byte) hash segments.
- TRACE_DATA event fires on response; 10-second timeout for no response.

**WebSocket Infrastructure (in place, not yet used):**
- Django Channels 4.2 with Redis channel layer (`127.0.0.1:6379`)
- ASGI routing: HTTP → Django ASGI app; `ws/monitoring/` → MonitoringConsumer
- MonitoringConsumer joins `"monitoring"` group on connect — ready for broadcast push

**Planned Data Flow for Telemetry (not yet implemented):**
- A background process will poll each active repeater on `MESHCORE_POLL_INTERVAL` seconds
- Poll results will be written to `RepeaterStats` (telemetry) and `NeighbourInfo` (topology)
- Changes will be broadcast via the `"monitoring"` WebSocket group to connected clients

**Encryption:**
- `django-encrypted-model-fields` is installed; encryption key is `base64(SHA-256(SECRET_KEY))`
- No fields are currently encrypted (was used for WiFi passwords in the removed hotspot feature)

**Deployment:**
- Targets Raspberry Pi running Daphne on port 8000 (`daphne -b 0.0.0.0 -p 8000 metro.asgi:application`)
- Self-signed HTTPS required for browser Geolocation API access
- See `docs/ARCHITECTURE.md` for full setup steps

## Security Considerations

- All POST/PATCH/DELETE API endpoints require Django CSRF token
- The app is designed for local network access only (no public exposure)
- Serial port access requires the running user to be in the `dialout` group on Linux
- `SECRET_KEY` and `.env` must not be committed — encryption key is derived from it
- Proof artifacts (screenshots, CLI output) should not contain real serial port paths or key material

## Success Metrics

1. **Accuracy**: A new developer can read this spec and correctly predict the behavior of every URL, API endpoint, and management command without running the code
2. **Completeness**: All currently-working features are covered; all known stubs are flagged as planned
3. **SDD-2 readiness**: The Demoable Units and Functional Requirements are specific enough to generate a concrete task list via `/SDD-2-generate-task-list-from-spec`

## Open Questions

1. Should `Node.estimated_range` be configurable via the UI? It currently defaults to 1000m and is only editable via Django admin or API.
2. The `firmware_version` field defaults to `"v1.9.1"` but is not updated by `load_radio_data` — is version sync desired in future?
3. `NeighbourInfo.snr` is stored as `SmallIntegerField` but the firmware multiplies SNR by 4 before sending — should the model store raw firmware value or divide by 4 on ingest?
