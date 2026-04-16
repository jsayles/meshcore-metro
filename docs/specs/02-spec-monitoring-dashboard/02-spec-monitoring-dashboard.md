# 02-spec-monitoring-dashboard

## Introduction/Overview

Add live mesh network monitoring to MeshCore METRO. A background poller periodically pings every repeater in the database, saves telemetry to `RepeaterStats`, and broadcasts results over WebSocket to any connected browser. The home page becomes the monitoring dashboard — a map showing each repeater colored by how recently it was heard, updating in real time as poll results arrive. Clicking a node opens a panel with its latest full telemetry.

## Goals

- Replace the static network overview with a live-updating monitoring dashboard at `/`
- Provide instant visual health status for every repeater using a color-coded freshness system
- Populate `RepeaterStats` with real telemetry data for the first time
- Deliver updates to the browser via WebSocket push (not browser polling)
- Keep the operator workflow simple: start the poller with one command, open the browser, done

## User Stories

**As a network operator**, I want to see all my repeaters on a map colored by how recently they responded so that I can spot problems at a glance without clicking anything.

**As a network operator**, I want the map to update automatically as new poll results arrive so that I don't have to refresh the page.

**As a network operator**, I want to click a repeater on the map to see its latest telemetry (signal, battery, packet counts) so that I can diagnose a degraded node.

**As a network operator**, I want to start monitoring with a single terminal command so that setup is not complicated.

## Demoable Units of Work

### Unit 1: Background Poller

**Purpose:** Continuously polls all active repeaters and saves telemetry to the database, forming the data backbone for monitoring.

**Functional Requirements:**
- The system shall provide a management command `python manage.py run_monitor` that starts the poller loop.
- The poller shall query all nodes where `is_active=true` and `role=REPEATER` at the start of each cycle (re-queried every cycle so newly-added nodes are picked up without restarting the poller).
- For each node the poller shall call `RadioInterface.get_current_signal(node)`, which uses `node.path` for routing and returns SNR to/from target and latency.
- On a successful response the poller shall create a `RepeaterStats` record with the returned signal values. Fields not available from a trace response (battery, packet counts, air time, errors) shall be left at their model defaults for now.
- On a failed response (timeout / no response) the poller shall log the failure; no `RepeaterStats` record is written for that cycle.
- The poller shall wait `MESHCORE_POLL_INTERVAL` seconds between cycles. The default value shall be changed to `60` seconds (from the current `5`).
- The command shall run until interrupted with Ctrl-C and log each poll result (node name, reachable/unreachable, SNR if available).
- After saving a result (success or failure), the poller shall broadcast a message to the `"monitoring"` Channels group containing: `node_id`, `last_seen` timestamp, and signal values (or null on failure).

**Proof Artifacts:**
- CLI: `python manage.py run_monitor` running with log lines like `[OK] Olympic Village — SNR ↑8.5 / ↓7.2` and `[--] Co-Food Gard — no response` demonstrates the poll loop
- Database: `RepeaterStats.objects.filter(node=<id>)` returning records after a poll cycle demonstrates data persistence

---

### Unit 2: Live Monitoring Dashboard

**Purpose:** Upgrades the home page to a live map dashboard that receives WebSocket push updates and re-colors nodes as poll results arrive.

**Functional Requirements:**
- The home page (`/`) shall remain map-centric with the existing Leaflet map and sidebar, reusing the current map rendering code.
- On page load the dashboard shall establish a WebSocket connection to `ws/monitoring/`.
- The `MonitoringConsumer` shall implement a `monitoring_update` handler that forwards broadcast messages from the `"monitoring"` group to connected WebSocket clients as JSON.
- Node markers shall be colored by the age of the node's most recent `RepeaterStats` record (falling back to `Node.last_seen` if no stats exist yet):
  - **Green** — last seen within 10 minutes
  - **Yellow** — last seen within 1 hour
  - **Red** — last seen more than 1 hour ago
- When a WebSocket message arrives for a node, the dashboard shall update that node's marker color and sidebar entry in place without reloading the page or re-fetching all nodes.
- The existing sidebar repeater list shall update the node's "last seen" time when a new result arrives.
- If the WebSocket connection drops, the dashboard shall attempt to reconnect with exponential backoff (1s, 2s, 4s… up to 30s max).

**Proof Artifacts:**
- Browser: home page showing map with color-coded markers updating in real time as the poller runs demonstrates end-to-end WebSocket push
- Browser DevTools Network tab: WebSocket frame arriving with node update JSON demonstrates the push path
- Browser: a node marker changing from red to green after the poller successfully pings it demonstrates live state update

---

### Unit 3: Node Telemetry Panel

**Purpose:** Lets the operator inspect the full latest telemetry for any repeater without leaving the dashboard.

**Functional Requirements:**
- Clicking a node marker or sidebar entry on the dashboard shall open a slide-in side panel (not navigate away from the page).
- The panel shall display the most recent `RepeaterStats` record for that node, including:
  - Reachable status and last seen timestamp
  - SNR to target / SNR from target (dB)
  - RSSI (dBm) and noise floor (dBm)
  - Battery voltage (V, converted from mV)
  - Packets received / sent (flood and direct counts)
  - Total air time TX / RX (seconds)
  - Error event count
- If no `RepeaterStats` record exists for the node, the panel shall display "No telemetry recorded yet."
- The panel shall update in place when a new WebSocket message arrives for the currently-selected node.
- The panel shall have a close button. Closing it returns to the plain map view.
- The existing "View Details" link (which navigates to `/node/<id>/`) shall remain available in the panel for full node management.

**Proof Artifacts:**
- Browser screenshot: clicking a node marker opens a panel showing telemetry values demonstrates the panel UI
- Browser: panel values updating while it is open (poller sends a new result) demonstrates live panel refresh
- Browser: "No telemetry recorded yet" shown for a node that has never been polled demonstrates the empty state

## Non-Goals (Out of Scope)

1. **Historical charts**: Time-series graphs of telemetry over time are planned but not part of this spec. Only the most recent `RepeaterStats` record per node is shown.
2. **Selective monitoring**: All active repeaters in the database are polled. Per-node opt-in/opt-out is not included.
3. **Auto-deactivation**: The poller will not automatically set `is_active=false` after repeated failures. Freshness color is the only failure signal.
4. **Full telemetry from radio**: `RepeaterStats` has fields for battery, packet counts, and air time that the trace/ping response does not provide. Those fields are populated with model defaults until a richer radio command is available.
5. **Auto-start with Daphne**: The poller is started manually via management command. Process supervision (systemd, supervisord) is out of scope.
6. **Configurable thresholds via UI**: Green/yellow/red thresholds are fixed (10 min / 1 hour). `.env` configuration is not included for thresholds.

## Design Considerations

**Map reuse:** The existing Leaflet map in `mesh_home.html` and `mesh-home.js` (`NodeOverview` class) is the starting point. The upgrade replaces the static color logic and adds the WebSocket connection and panel overlay — it does not rewrite the map from scratch.

**Side panel:** Slides in from the right, overlaying the map (not pushing it). Width ~320px on desktop, full-width on mobile. Dismissible with a close button or by clicking the map.

**Color thresholds (fixed values):**
- Green: `last_seen` within 600 seconds (10 minutes)
- Yellow: `last_seen` within 3600 seconds (1 hour)
- Red: `last_seen` older than 3600 seconds

**CSS:** New panel and indicator styles added to `mesh-home.css` using existing CSS variables. No new color values hardcoded.

## Repository Standards

- Management command follows the pattern in `metro/management/commands/` (class-based, `add_arguments` + `handle`)
- `RadioInterface` used as async context manager matching existing pattern in `api/views.py`
- WebSocket consumer extends `AsyncWebsocketConsumer` matching the existing `MonitoringConsumer` stub
- API responses remain GeoJSON where applicable; WebSocket messages are plain JSON
- CSS variables used for all colors — no hardcoded hex values
- Poll interval read from `settings.MESHCORE_POLL_INTERVAL` (set via `.env`)

## Technical Considerations

**Poller architecture:** The management command runs an `asyncio` event loop. Each cycle iterates nodes sequentially (not concurrently) to avoid saturating the radio. After each node result it calls `async_to_sync(channel_layer.group_send)` or runs fully async — whichever fits cleanly with the existing `RadioInterface` usage pattern.

**WebSocket message shape (poller → browser):**
```json
{
  "type": "monitoring.update",
  "node_id": 1,
  "reachable": true,
  "last_seen": "2026-04-08T14:32:00Z",
  "snr_to_target": 8.5,
  "snr_from_target": 7.2,
  "latency_ms": 342
}
```
On failure: `reachable: false`, SNR fields `null`.

**Consumer handler:** `MonitoringConsumer` needs a `monitoring_update` method that receives the group broadcast and calls `self.send(text_data=json.dumps(event))` to forward it to the browser. The `type` key `"monitoring.update"` maps to the method name `monitoring_update` per Channels convention.

**`MESHCORE_POLL_INTERVAL` default:** Update the default in `settings.py` from `5` to `60`. Document in `.env.example` or equivalent.

**RepeaterStats fields populated by this spec:**
- `node` — the polled node
- `timestamp` — auto-set on create
- `last_snr` — SNR to target from trace response (`path[0].snr`)
- `last_rssi`, `noise_floor`, `batt_milli_volts`, `curr_tx_queue_len`, `n_packets_*`, `total_*_secs`, `err_events` — left at model defaults (0). The meshcore trace response only contains SNR per hop; RSSI, battery, and packet stats require a separate `STATS` command which is out of scope for this spec.

## Security Considerations

- WebSocket endpoint (`ws/monitoring/`) is wrapped in `AuthMiddlewareStack` already — no additional auth needed for local network use
- No sensitive data (keys, passwords) flows through the monitoring WebSocket
- Poll results stored in `RepeaterStats` contain signal metrics only — no PII or credentials

## Success Metrics

1. **Poller runs**: `python manage.py run_monitor` starts without error, logs poll results for all active repeaters each cycle
2. **Data saved**: `RepeaterStats` table accumulates records over time while the poller is running
3. **Live updates**: Browser map markers change color in real time as poll results arrive, without page refresh
4. **Panel works**: Clicking any node on the dashboard shows its latest telemetry values

## Open Questions

No open questions at this time.
