# CrisisRoute

Academic AI project. Disaster-response decision-support system: given a
synthetic crisis scenario (hazard zones, road network, population centers,
available resources), the system assesses risk, allocates limited resources,
and routes them to where they're needed, replanning as conditions change.

This file is the scope reference for incremental review milestones. Review 1
targets 60% of the system as scoped below.

## Review 1 scope (in)

- **Synthetic scenario generator** — produces reproducible crisis scenarios
  (graph-based road network, hazard zones, population/demand nodes, resource
  depots) for use by every other module and by the evaluation script.
- **Bayesian Network risk assessment** — probabilistic risk scoring over
  scenario variables (e.g. hazard severity, proximity, population density)
  using pgmpy.
- **Genetic Algorithm resource allocation**, with a **greedy baseline** for
  comparison — allocates limited resources (vehicles, supplies, personnel)
  across demand nodes. The GA itself is hand-written (see DEVELOPMENT.md
  rule on no library implementations for GA/search).
- **Routing**: A*, BFS, DFS implemented by hand over the scenario's road
  network graph.
- **Dynamic replanning** — reroutes/reallocates when the scenario changes
  mid-run (e.g. a route becomes blocked, a hazard zone expands).
- **Flask API with SQLite** — exposes scenario, risk, allocation, and
  routing results; persists scenarios/runs.
- **React + Leaflet dashboard** — visualizes the scenario map, risk scores,
  allocations, and routes.
- **Evaluation script** — runs the pipeline end-to-end over generated
  scenarios and reports metrics (e.g. GA vs. greedy allocation quality,
  routing cost/time, replanning responsiveness).

## Out of scope for now

- Multi-agent layer
- PostgreSQL/PostGIS
- Real OSM (OpenStreetMap) data
- Feedback learning
- Alerts

## Repo layout

```
backend/crisisroute/
  scenario/      synthetic scenario generator
  risk/          Bayesian Network risk assessment
  allocation/    GA resource allocation + greedy baseline
  routing/       A*, BFS, DFS
  replanning/    dynamic replanning
  api/           Flask API + SQLite
backend/tests/   pytest tests, mirroring the above modules
frontend/        React + Leaflet dashboard
eval/            evaluation script
```

See [DEVELOPMENT.md](../DEVELOPMENT.md) for coding rules (no comments,
hand-written GA/search, seeded reproducibility, pytest coverage per module).

## 7. `flood_demo` preset

A fixed, reproducible scenario (seed `20261008`) used by the dashboard and
the evaluation script as a standard worked example. It reuses the normal
~80-node jittered Chennai road network, but overrides the zones and
resources with fixed values instead of random ones:

**Zones A–D**

| Zone | Node area | Population | Vulnerable % | Water level | Rainfall | Infra. condition | Road access |
|------|-----------|-----------:|-------------:|------------:|---------:|-------------------|--------------|
| A | Velachery | 18,000 | 22.5% | 1.8 m | 180 mm | damaged | limited |
| B | Saidapet | 12,000 | 15.0% | 1.2 m | 140 mm | damaged | accessible |
| C | Kotturpuram | 9,000 | 28.0% | 2.4 m | 210 mm | critical | cutoff |
| D | Adyar | 15,000 | 18.5% | 1.5 m | 160 mm | damaged | limited |

**Resources** — 2 depots, resources split across them:

- `AMB-1`, `AMB-2` — ambulances, capacity 2, at Depot 1
- `RESCUE-1` — rescue team, capacity 6, at Depot 1
- `RESCUE-2` — rescue team, capacity 6, at Depot 2
- `RELIEF-1` — relief vehicle, capacity 40, at Depot 2

**Hospitals** — 2, fixed capacity: City General Hospital (150), Riverside
Hospital (100).

Zone and depot/hospital node placements are chosen deterministically from
the generated network (fixed seed), so `load_preset("flood_demo")` always
returns the identical scenario.
