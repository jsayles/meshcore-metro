# 01 Questions Round 1 - MeshCore Metro Current State

Please answer each question below (select one or more options, or add your own notes). Feel free to add additional context under any question.

## 1. Purpose of this Spec

This spec documents the existing application as-is. What will it primarily be used for?

- [X] (A) Foundation for planning new features (will feed into SDD-2 task generation)
- [ ] (B) Onboarding reference for new contributors
- [ ] (C) Baseline before a significant refactor
- [ ] (D) All of the above
- [ ] (E) Other (describe)

## 2. Known Incomplete Features

The codebase has several stub/placeholder areas. Should the spec flag these as intentional gaps or out-of-scope items?

- [] (A) Yes — flag them explicitly as "not yet implemented" so they appear in Non-Goals
- [ ] (B) No — only document what currently works; ignore stubs entirely
- [X] (C) Flag them but note they are planned (so future specs can reference them)

Known stubs I found:
- `MonitoringConsumer` (WebSocket) — connects and joins group but has no message handlers
- `RepeaterStats` model — schema exists and is admin-registered but no code writes to it
- `NeighbourInfo` model — schema exists and is admin-registered but no code writes to it
- `MESHCORE_POLL_INTERVAL` setting — defined but nothing polls on that interval

## 3. Node.path Business Rules

The `path` field on Node drives how pings/traces are routed. I documented it from the code, but want to confirm the rules:

- [X] (A) Blank = flood ping (broadcasts mesh-wide) — current behavior is correct
- [X] (B) 2-char hex string (e.g., `"46"`) = 1-byte direct hash — correct
- [X] (C) Comma-separated 2-char hashes (e.g., `"46,93,46"`) = multi-hop fixed route — correct
- [ ] (D) One or more of the above need correction — add notes below

Notes: The system has evolved to allow 4 and 6 char hashes as well.  

## 4. Telemetry / Stats Collection

`RepeaterStats` stores per-poll telemetry (battery, RSSI, SNR, packet counts) but I found no code that currently writes to this table. What is the intent?

- [x] (A) It's designed for a future background poller — document as planned, not active
- [ ] (B) There is an existing polling mechanism I missed — point me to it
- [ ] (C) It's legacy / may be removed — document as unused
- [ ] (D) Other (describe)

## 5. Deployment Target

The app is described as running on a Raspberry Pi. Should the spec document deployment steps and hardware constraints?

- [ ] (A) Yes — include deployment as a first-class section (Daphne, Redis, PostGIS, .env, HTTPS)
- [ ] (B) No — keep spec focused on application behavior only; deployment lives in README/ARCHITECTURE.md
- [X] (C) Brief reference only — mention Raspberry Pi + Daphne but don't duplicate ARCHITECTURE.md

## 6. Out-of-Scope Boundaries

The UI references a "WiFi Hotspot Configuration" section in comments/memory but I found no such view, model, or template in the current code. Should the spec:

- [X] (A) Note it as explicitly removed/not yet built (Non-Goal)
- [ ] (B) Ignore it entirely since there's no code
- [ ] (C) Other (describe)

It was removed.  Emphasis was shifted away from field testing to monitoring only which does not require the hotspot. 

## 7. Success Metrics

For a "current state" spec, success means the documentation accurately represents what exists. What does "done" look like to you?

- [X] (A) Spec is accurate enough for a new developer to understand and run the app
- [X] (B) Spec is accurate enough to feed into SDD-2 task generation for new features
- [X] (C) Spec serves as acceptance criteria for regression testing the current behavior
- [X] (D) All of the above
- [ ] (E) Other (describe)
