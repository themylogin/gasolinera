# Proposal

## Why

Gasolinera must know where Spanish fuel stations are and what they charge. The MITECO REST service publishes every station of Spain, with its position, opening hours, and current prices, in one JSON answer. `french_tolls` already has a `gas-stations` run for the French source, and this change copies its pattern.

## What Changes

- Add a one-shot `gas-stations` run. It downloads the full MITECO station list in one request and replaces the stored stations with it in one transaction.
- Store each station: its id, position, brand, address fields, opening hours, and every non-empty price field exactly as the feed sends it.
- Skip stations with coordinates outside Spain. The feed of 07/11/2026 has five of them.
- Delete a stored station when the feed no longer lists it.
- Add a geographic index for area queries, kept equal to the station table by triggers, as in `french_tolls`.
- Add a fuel map in the code with three groups: `gasoline_95`, `gasoline_98`, `diesel`. A function gives the cheapest price of a group at a station, and names the source field it came from.
- Add `httpx` as a direct dependency. It is already pinned as a dependency of `python-telegram-bot`.

Out of scope:

- The bot dialogue that lets a user choose a fuel group.
- Any fuel outside the three groups: LPG, CNG, LNG, E85, hydrogen, AdBlue, Gasoleo B, biodiesel.
- A schedule. The operator starts each run.
- Route search along stations.

## Capabilities

### New Capabilities

- `gas-station-inventory`: the MITECO download, what the store keeps for each station, the replace rules, and the area query.
- `fuel-groups`: the three fuel groups, the source fields of each, and the cheapest price of a group at a station.

### Modified Capabilities

- `runtime-store`: the store now has the station table and its geographic index. A hand-written statement is allowed in a revision for the index and its triggers. A fresh store records the latest revision, not the baseline.

## Impact

- New code: `gasolinera/gas_stations.py`, `gasolinera/fuels.py`, a model, an Alembic revision, tests.
- New Compose service `gas-stations` and Make target `gas-stations`.
- `README.md` gets a section on the run.
- Network: one 12 MB request to `sedeaplicaciones.minetur.gob.es` per run.
- The existing store test that expects no application table changes.
