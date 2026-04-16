# 02-tasks-monitoring-dashboard

## Relevant Files

- `metro/management/commands/run_monitor.py` — New file. The `run_monitor` management command (background poller).
- `metro/consumers.py` — Add `monitoring_update` handler to complete the WebSocket consumer.
- `metro/settings.py` — Change `MESHCORE_POLL_INTERVAL` default from `5` to `60`.
- `api/views.py` — Add `latest_stats` action to `NodeViewSet` for the telemetry panel.
- `metro/static/metro/js/mesh-home.js` — Upgrade `NodeOverview` class: new thresholds, WebSocket connection, live marker updates.
- `metro/templates/metro/mesh_home.html` — Add telemetry panel HTML.
- `metro/static/metro/css/mesh-home.css` — Add telemetry panel and status indicator styles.

### Notes

- Follow the existing management command pattern: class-based `Command` with `help`, `add_arguments`, and `handle`.
- Use `asyncio.run()` in `handle()` to run the async poll loop (cleaner than `new_event_loop()` used in views).
- Django ORM calls inside an async function must be wrapped with `sync_to_async` from `asgiref.sync`.
- The Channels `channel_layer` is available via `from channels.layers import get_channel_layer`.
- All CSS color values must use CSS variables from `metro.css` — no hardcoded hex values.
- The `nodeMarkerMap` in `NodeOverview` is already keyed by node ID — use it for all WS-driven updates.

## Tasks

### [ ] 1.0 Background Poller

Build the `run_monitor` management command that drives all monitoring. It loops over every active repeater each cycle, pings it via the radio, saves a `RepeaterStats` record on success, and broadcasts the result to the Channels `"monitoring"` group.

#### 1.0 Proof Artifact(s)

- CLI: `python manage.py run_monitor` running in a terminal showing log lines like `[OK] Olympic Village — SNR ↑8.5 / ↓7.2` and `[--] Co-Food Gard — no response` demonstrates the poll loop
- Database: Django shell `RepeaterStats.objects.filter(node__name="Olympic Village").count()` returning a non-zero value after one or more poll cycles demonstrates data persistence
- Log: startup output showing the configured poll interval demonstrates `MESHCORE_POLL_INTERVAL` is being read

#### 1.0 Tasks

- [ ] 1.1 In `metro/settings.py`, change the `MESHCORE_POLL_INTERVAL` default from `5` to `60` (seconds).
- [ ] 1.2 Create `metro/management/commands/run_monitor.py` with a `Command` class, a `help` string describing the command, and a `handle()` method that calls `asyncio.run(self._poll_loop())`.
- [ ] 1.3 Implement `_poll_loop()` as an `async` method: log startup with the configured interval, then enter a `while True` loop that fetches all active repeaters using `await sync_to_async(list)(Node.objects.filter(is_active=True, role=Role.REPEATER))` at the top of each cycle.
- [ ] 1.4 Inside the loop, open `RadioInterface` as an async context manager and iterate over the node list sequentially, calling `await radio.get_current_signal(node)` for each node.
- [ ] 1.5 On a successful result: create a `RepeaterStats` record using `sync_to_async` with `node=node` and `last_snr=result["snr_to_target"]`; update `Node.last_seen` to `timezone.now()` using `sync_to_async`.
- [ ] 1.6 Build a broadcast dict matching the spec's message shape and call `await channel_layer.group_send("monitoring", {...})` after each node result — success sends SNR values, failure sends `"reachable": false` with `null` SNR fields.
- [ ] 1.7 Log each result to stdout using `self.stdout.write()`: `[OK] {name} — SNR ↑{snr_to} / ↓{snr_from}` on success, `[--] {name} — no response` on failure.
- [ ] 1.8 After iterating all nodes, log a cycle summary (`Cycle complete — {n} nodes polled`) then `await asyncio.sleep(settings.MESHCORE_POLL_INTERVAL)`.
- [ ] 1.9 Wrap the `while True` loop in `try/except KeyboardInterrupt` so Ctrl-C prints a clean shutdown message instead of a traceback.

---

### [ ] 2.0 WebSocket Consumer

Complete the `MonitoringConsumer` stub so it forwards poller broadcasts to connected browser clients. This is the wire between the backend poller and the frontend dashboard.

#### 2.0 Proof Artifact(s)

- Browser DevTools → Network → WS → `ws/monitoring/` → Messages tab: a JSON frame arriving with `{ "node_id": ..., "reachable": ..., "last_seen": ..., "snr_to_target": ... }` while the poller is running demonstrates the full push path from radio → database → WebSocket → browser

#### 2.0 Tasks

- [ ] 2.1 Add `import json` to `metro/consumers.py` if not already present.
- [ ] 2.2 Add an async `monitoring_update(self, event)` method to `MonitoringConsumer`. It should build a payload dict from `event`, remove the `"type"` key (it's for Channels routing, not the browser), and call `await self.send(text_data=json.dumps(payload))`.

---

### [ ] 3.0 Live Monitoring Dashboard

Upgrade the home page map to connect to the WebSocket, color node markers by freshness using the new thresholds, and update markers and the sidebar in place as push messages arrive — no page reload.

#### 3.0 Proof Artifact(s)

- Browser screenshot: home page (`/`) showing map with color-coded markers (green/yellow/red) and matching sidebar entries demonstrates freshness coloring with new thresholds
- Browser: a node marker visibly changing color after the poller successfully pings it, without a page refresh, demonstrates live update
- Browser DevTools → Console: no errors after the WebSocket connection is intentionally closed and automatically reconnects demonstrates reconnect backoff

#### 3.0 Tasks

- [ ] 3.1 In `mesh-home.js`, update `getNodeColor()` to use the new thresholds: green if `secondsSince < 600` (10 minutes), yellow if `secondsSince < 3600` (1 hour), red otherwise. Switch from hours to seconds in the calculation.
- [ ] 3.2 Update `getStatusLabel()` to match: return `"Current"` if < 10 min, `"Recent"` if < 1 hour, `"Stale"` otherwise.
- [ ] 3.3 Update `renderRepeaterList()` to use the new "Current" threshold (< 10 min) when filtering which nodes appear in the sidebar, and update the `data-last-seen` attribute on each `<li>` so it can be updated later.
- [ ] 3.4 Add a `connectWebSocket()` method to `NodeOverview`. It should build the correct URL (`ws://` or `wss://` based on `window.location.protocol`), open a `WebSocket`, and set `onmessage`, `onclose`, and `onerror` handlers.
- [ ] 3.5 In the `onmessage` handler, parse the JSON payload and call a new `handleMonitoringUpdate(data)` method.
- [ ] 3.6 Implement `handleMonitoringUpdate(data)`: look up the node in `nodeMarkerMap` by `data.node_id`; if found, update the stored node's `last_seen` to `data.last_seen`, compute the new color with `getNodeColor()`, and update the marker icon and circle style with the new color.
- [ ] 3.7 Also in `handleMonitoringUpdate`: find the sidebar `<li>` for this node by its `data-node-id` attribute and update its displayed "last seen" text.
- [ ] 3.8 Implement exponential backoff reconnect in the `onclose` handler: start at 1 second, double each attempt up to a 30-second maximum, then call `connectWebSocket()` again.
- [ ] 3.9 Call `this.connectWebSocket()` at the end of `init()`, after `loadNodes()` completes.

---

### [ ] 4.0 Node Telemetry Panel

Add a slide-in panel that opens when a node is clicked, shows its latest `RepeaterStats` from a new API endpoint, and refreshes live when the WebSocket delivers a new result for the selected node.

#### 4.0 Proof Artifact(s)

- Browser screenshot: clicking a node marker opens a right-side panel displaying SNR, battery voltage, packet counts, and a "View Details" link demonstrates the panel UI and data display
- Browser: panel values updating in place (without closing and reopening) when the poller sends a new result for the selected node demonstrates live panel refresh
- Browser screenshot: panel showing "No telemetry recorded yet." for a node that has never been polled demonstrates the empty state

#### 4.0 Tasks

- [ ] 4.1 In `api/views.py`, add a `latest_stats` action to `NodeViewSet`: `@action(detail=True, methods=["get"])`. It should fetch `RepeaterStats.objects.filter(node=node).order_by("-timestamp").first()` and return its fields as plain JSON (not GeoJSON). Return `{"stats": null}` if no record exists.
- [ ] 4.2 Add the telemetry panel HTML to `metro/templates/metro/mesh_home.html`: a `<div id="telemetry-panel">` with a close button, a node name heading, a stats grid (SNR to/from, RSSI, noise floor, battery voltage, flood/direct packet counts, TX/RX air time, errors), a "No telemetry recorded yet." empty state div, and a "View Details" `<a>` link. The panel should be hidden by default (`display: none`).
- [ ] 4.3 Add panel styles to `mesh-home.css`: fixed right-side position, width 320px, full height, overlays the map (not pushing it), slides in from the right using a CSS transition, `z-index` above the map, uses `--bg-color` and `--border-color` variables. On mobile (max-width 600px), panel should be full width.
- [ ] 4.4 Add an `openPanel(nodeId, nodeName)` method to `NodeOverview`: show the panel, set the node name heading, set the "View Details" href to `/node/{nodeId}/`, store `this.selectedNodeId = nodeId`, then fetch `/api/v1/nodes/{nodeId}/latest_stats/` and call `renderPanelStats(stats)`.
- [ ] 4.5 Implement `renderPanelStats(stats)`: if `stats` is `null`, show the empty state div and hide the stats grid; otherwise populate each field in the grid (convert `batt_milli_volts` to volts by dividing by 1000, format SNR with one decimal place) and show the grid.
- [ ] 4.6 Add a `closePanel()` method: hide the panel, clear `this.selectedNodeId`.
- [ ] 4.7 Wire up node clicks: in `renderNodes()`, add a click listener to each marker that calls `this.openPanel(node.id, props.name)` instead of (or in addition to) the popup. In `renderRepeaterList()`, update sidebar `<li>` click handlers to call `this.openPanel(node.id, nodeName)` as well.
- [ ] 4.8 In `handleMonitoringUpdate(data)`, after updating the marker color, check if `this.selectedNodeId === data.node_id`; if so, call `renderPanelStats(data)` to refresh the open panel in place.
- [ ] 4.9 Wire the close button to call `closePanel()`. Add a click listener on the map itself that calls `closePanel()` when the user clicks the map background (not a marker).
