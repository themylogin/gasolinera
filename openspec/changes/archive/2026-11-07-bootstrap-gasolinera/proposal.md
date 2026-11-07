# Proposal

## Why

Gasolinera is a new project with no code yet. It needs a minimal, runnable base that reuses the proven practices of `french_tolls`. Later changes then add features on top of a working stack.

## What Changes

- Add a container-only project layout: `Dockerfile`, `docker-compose.yml`, `Makefile`, `.env.example`, `.gitignore`, `.dockerignore`, `README.md`.
- Add one OSRM query service, `osrm`. It serves a graph built from the Geofabrik extract of Spain with the default car profile of the OSRM image.
- Add two build steps: `download_pbf` and `setup_osrm`. Each step skips work that is already complete.
- Add an SQLite store with no application tables. Alembic versions the schema from the first revision. A one-shot `migrate` run applies it.
- Add a Telegram bot process that starts, polls Telegram, and registers no handlers.
- Add a pinned dependency list, compiled from `pyproject.toml` by `make requirements`.
- Add a unit test suite that runs in a container through `make test`.

Out of scope:

- Any OSRM profile patch, a second graph, or a relay.
- Any table in the store.
- Any bot command or reply.
- A web service, a front end, and integration tests.

## Capabilities

### New Capabilities

- `routing-service`: the Spain extract, the build steps that make the graph, and the `osrm` query service.
- `runtime-store`: the SQLite file, its versioned schema, and the one run that applies the schema.
- `telegram-bot`: the bot process, its configuration, and its start rules.
- `project-tooling`: the container-only layout, the `.env` configuration, the pinned dependencies, and the test run.

### Modified Capabilities

None. The project has no specs yet.

## Impact

- New files in `gasolinera/` only. No change to `french_tolls`.
- New host requirements: Docker, the Compose plugin, GNU make.
- New disk use outside the repository at `OSRM_PATH`, 3.4 GB for the Spain graph.
- New external dependencies: Geofabrik for the extract, the Telegram Bot API, the OSRM image `ghcr.io/project-osrm/osrm-backend:26.8-debian`.
