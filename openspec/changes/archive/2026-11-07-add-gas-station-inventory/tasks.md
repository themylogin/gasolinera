# Tasks

## 1. Dependency

- [x] 1.1 Add `httpx` to `dependencies` in `pyproject.toml` and run `make requirements`. Verify that `requirements.txt` lists `httpx` with `# via gasolinera (pyproject.toml)` and that no other pin changes.

## 2. Fuel groups

- [x] 2.1 Create `gasolinera/fuels.py` with `FUEL_GROUPS` and `group_price(prices, group)` as `design.md` describes.
- [x] 2.2 Write `gasolinera/tests/test_fuels.py` with one test per `fuel-groups` scenario. Include `"NaN"` as a text that is not a price. Verify that `make test` passes.

## 3. Schema

- [x] 3.1 Add `GasStation` and `GasStationArea` to `gasolinera/models.py` with the columns of `design.md`.
- [x] 3.2 Add the `include_object` filter for `gas_station_area*` to `alembic/env.py`.
- [x] 3.3 Generate the revision `gas_stations` in a container. Fill it from the `french_tolls` revision with the new columns, the R*Tree, the three triggers, and the batch warning. Verify that its filename starts with the date and time and that `down_revision` is `d13b3f5e580d`.
- [x] 3.4 Run `alembic check` in a container on a migrated store. Verify that it reports no difference between the models and the revisions.
- [x] 3.5 Update `gasolinera/tests/test_store.py`: the tables of a fresh store and the latest revision id, both as literals. Add a test that only the revision has `CREATE VIRTUAL TABLE` or `CREATE TRIGGER`. Verify that `make test` passes.

## 4. The download run

- [x] 4.1 Save `gasolinera/tests/miteco_sample.json` from a live fetch: the feed header, and the entries with `IDEESS` 4375, 11988, 16268, and one Canary Islands station. Verify that the file is valid JSON and that each entry has 41 fields.
- [x] 4.2 Create `gasolinera/gas_stations.py` with `parse_entry`, `update(transport=None)`, `stations_in_area`, and `main`, as `design.md` describes.
- [x] 4.3 Write `gasolinera/tests/test_gas_stations.py` with the Alembic-migrated `tmp_path` store and `httpx.MockTransport`. Cover each `gas-station-inventory` scenario except the Compose ones. Include the request count, the log of the counts, the query plan, and the three trigger cases. Verify that `make test` passes.

## 5. Compose and documentation

- [x] 5.1 Add the `gas-stations` service to `docker-compose.yml`, add the profile `gas-stations` to `migrate`, and add the `gas-stations` target to the `Makefile`. Verify that `docker compose config` succeeds with no `.env` and that `docker compose up -d` starts only `osrm`.
- [x] 5.2 Add a "Gas stations" section to `README.md` with `make gas-stations` and the source address. Verify that the target exists in the `Makefile`.

## 6. Integration checks

- [x] 6.1 Run `make gas-stations` against the live service. Verify that it exits with 0, logs the feed date, and logs about 11,470 stored and 5 skipped stations.
- [x] 6.2 In the `cache` volume, verify that `gas_station` and `gas_station_area` have the same row count. Verify that `stations_in_area` for the box south 40.3, west -3.8, north 40.5, east -3.6 returns stations in Madrid. Verify that `group_price` gives a `diesel` price for most of them.
- [x] 6.3 Run `make gas-stations` a second time. Verify that the row count stays the same and that every `updated_at` equals the time of the second run.
