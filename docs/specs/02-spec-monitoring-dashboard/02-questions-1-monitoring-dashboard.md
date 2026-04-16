# 02 Questions Round 1 - Monitoring Dashboard

Please answer each question below. Feel free to add notes under any question.

## 1. Dashboard Location

Where should the monitoring dashboard live?

- [X] (A) Replace the current home page (`/`) — monitoring IS the home page
- [ ] (B) New page at `/monitoring/` — home page stays as the map overview
- [ ] (C) Other (describe)

## 2. What Data to Show Per Node

For each repeater being monitored, what should be visible on the dashboard?

- [ ] (A) Signal quality only — RSSI, SNR, reachable/unreachable status
- [ ] (B) Signal + battery — RSSI, SNR, battery voltage, reachable status
- [ ] (C) Full telemetry — everything in `RepeaterStats` (RSSI, SNR, battery, packet counts, air time, errors)
- [X] (D) Other (describe)

Show the system is alive and the last time we got proof of life.  We should have thresholds and indicators.  Seen in the last 10 min the node shows green.  In the last hour, shows yellow.  Otherwise red.   When you click on a node it shows C, full telemetry.  

## 3. Dashboard Layout

How should nodes be presented?

- [ ] (A) Card grid — one card per repeater, updates in place as data arrives
- [ ] (B) Table — rows per repeater, columns for each metric
- [X] (C) Map-centric — nodes on map, click to see live stats in a panel
- [ ] (D) Other (describe)

The map is already written and working. 

## 4. Poll Interval

How often should the poller ping each repeater?

- [ ] (A) 30 seconds
- [ ] (B) 60 seconds
- [ ] (C) 5 minutes
- [ ] (D) Configurable via UI
- [X] (E) Use the existing `MESHCORE_POLL_INTERVAL` setting (currently defaults to 5s — probably needs adjusting)
- [ ] (F) Other (describe)

Notes:  I want a baseline of settings to work to get this up and running quickly but make it easy to update via changing your .env file before deploy.  

## 5. Which Nodes Get Polled

- [X] (A) All active repeaters (`is_active=true`, `role=REPEATER`) — poll everything in the database
- [ ] (B) Only nodes the operator explicitly enables for monitoring
- [ ] (C) Other (describe)

All nodes in the database should be considered part of "My Mesh".  If I added them (via config) it means I want to monitor them.  

## 6. Failed Poll Handling

What should happen when a repeater doesn't respond (10s timeout)?

- [ ] (A) Mark it visually as unreachable on the dashboard, keep trying next cycle
- [ ] (B) Mark unreachable + after N consecutive failures, mark `is_active=false` on the Node
- [ ] (C) Just log it, no visual change
- [x] (D) Other (describe)

I described the color system in answer #2

## 7. How the Poller Runs

The background poller needs to run alongside Django. How should it start?

- [X] (A) Management command (`python manage.py run_monitor`) — operator starts it manually in a separate terminal
- [ ] (B) Starts automatically when Daphne starts (via Channels `ready()` signal or startup hook)
- [ ] (C) Other (describe)

## 8. Historical Data

`RepeaterStats` is designed to accumulate readings over time. Should the dashboard show history?

- [X] (A) Live only — just the most recent reading per node, no history view
- [ ] (B) Sparkline / mini chart — show last N readings as a trend line per metric
- [ ] (C) Full chart — time-series graph for selected node
- [ ] (D) Other (describe)

Option C we can do at a future time.  Right now just the most recent.  