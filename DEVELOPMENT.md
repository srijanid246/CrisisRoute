# Development Notes

Project reference for working on CrisisRoute. See [docs/PROJECT.md](docs/PROJECT.md)
for the full project description.

## Scope — Review 1 (60%, complete)

Already built and in the repo. Stays in scope — must keep working:
- Synthetic scenario generator
- Bayesian Network risk assessment (pgmpy)
- Genetic Algorithm resource allocation, with a greedy baseline
- A*/BFS/DFS routing
- Dynamic replanning
- Flask API with SQLite
- React + Leaflet dashboard
- Evaluation script

## Scope — Review 2 (100%)

Everything previously out of scope is now in scope, to be built in this
order:

1. Evaluation fixes
2. Multi-agent simulation layer
3. Simulation dashboard
4. Real OpenStreetMap data
5. PostgreSQL/PostGIS
6. Feedback and learning
7. Alerts and scenario comparison
8. Final evaluation and docs

Build in this order, one item at a time. Existing tests must keep passing
after every step — run the full suite before moving on to the next item.

## Rules

- **No comments in code.** Code must read clearly from naming and structure
  alone. This applies to Python, JS/TSX, and config/scripts alike.
- **GA and search algorithms are hand-written.** No library implementations
  for the Genetic Algorithm or for A*/BFS/DFS routing (no `networkx`,
  `deap`, etc. for these). Everything else (Flask, SQLAlchemy, pgmpy, numpy,
  matplotlib, React, Leaflet) is used normally.
- **Everything is seeded and reproducible.** Any randomness (scenario
  generation, GA population/mutation, etc.) takes an explicit seed, and the
  same seed must reproduce the same output.
- **Every module gets pytest tests.** Tests live under `backend/tests/`,
  mirroring the `backend/crisisroute/` package layout.

## Repo layout

```
backend/crisisroute/
  scenario/      synthetic scenario generator
  risk/          Bayesian Network risk assessment
  allocation/    GA resource allocation + greedy baseline
  routing/       A*, BFS, DFS
  replanning/    dynamic replanning
  api/           Flask API + SQLite
backend/tests/   pytest tests
frontend/        React + Leaflet dashboard
eval/            evaluation script
```

## Environment

- Python venv at `backend/venv`, dependencies in `backend/requirements.txt`
  (flask, flask-cors, sqlalchemy, pgmpy, numpy, matplotlib, pytest).
