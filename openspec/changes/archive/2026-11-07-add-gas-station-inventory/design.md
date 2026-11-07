# Design

## Context

`french_tolls/french_tolls/gas_stations.py` reads a list of French stations and then one HTML page per stale station. It stores each station in its own transaction and keeps an R*Tree index through triggers.

The Spanish source is simpler. One GET to `…/EstacionesTerrestres/` returns every station with its prices. A fetch on 07/11/2026 showed these facts:

- 11,479 entries, 12 MB, 2.5 s. No BOM, no compression.
- Every entry has the same 41 fields. No `IDEESS` repeats. The largest id is 16550.
- Numbers use a decimal comma: `"39,211417"`, `"1,799"`. An unsold fuel is `""`.
- Five entries have bad coordinates: four at `0,000000`, and one with latitude and longitude swapped.
- A filter with no match answers `200` with `"ResultadoConsulta": "OK"` and an empty list.
- The `Content-Type` is `text/html` or `application/json`, depending on the `Accept` header.
- The service accepts any User-Agent.

This change keeps from `french_tolls`: the station model, the R*Tree revision with its triggers, the area query, the one-shot Compose service, and the test style with an Alembic-migrated temporary store.

It drops: per-station requests, the maximum age, the concurrency limit, per-station transactions, `aiohttp`, `isodate`, and BeautifulSoup.

## Goals / Non-Goals

**Goals:**

- One run gives a store that equals the feed, minus the invalid entries.
- The raw prices stay as the feed sends them, so a new fuel field or a new group needs no migration.

**Non-Goals:**

- Price history. Each run replaces the previous prices.
- Converting the feed `Fecha` to UTC. The run only logs it.

## Decisions

### HTTP client: httpx

`httpx` is already pinned as a dependency of `python-telegram-bot`. The change declares it in `pyproject.toml` because the code imports it, and it adds no new package.

`update(transport=None)` passes the transport to `httpx.AsyncClient`. A test then gives `httpx.MockTransport`, and no test reaches MITECO.

Alternative: `aiohttp` with a local `TestServer`, as in `french_tolls`. Rejected, because it adds a package for one request.

The run parses `json.loads(response.content)` and does not use the `Content-Type`, because the server sends `text/html` for JSON.

### One transaction replaces the whole set

The run parses and checks the whole feed before it opens the store. Then, in one transaction, it runs `DELETE FROM gas_station` and inserts every valid entry. The triggers keep the index equal.

WAL lets a reader see the old set until the commit. A failed fetch or parse returns before the transaction, so the store does not change.

Alternative: upsert, then delete the ids that the feed does not list. Rejected. The result is the same, the code is longer, and the old set stays visible in both cases.

### The station model

| Column | Type | Source |
| --- | --- | --- |
| `id` | Integer, primary key, no autoincrement | `IDEESS` |
| `latitude` | Float | `Latitud` |
| `longitude` | Float | `Longitud (WGS84)` |
| `name` | Text | `Rótulo` |
| `address` | Text | `Dirección` |
| `postal_code` | Text | `C.P.` |
| `locality` | Text | `Localidad` |
| `municipality` | Text | `Municipio` |
| `province` | Text | `Provincia` |
| `opening_hours` | Text | `Horario` |
| `prices` | JSON object | every non-empty `Precio …` field, name and text unchanged |
| `updated_at` | DateTime, naive UTC | the time the run received the answer |

All text columns are `NOT NULL`. The run stores an empty string when the feed has one.

The table does not keep `Margen`, `Remisión`, `Tipo Venta`, the bio percentages, or the id fields of the region. Nothing needs them yet. A later revision can add a field, and the next run fills it.

### The entry check

An entry is valid when `IDEESS` is an integer, both coordinates parse after the comma becomes a point, latitude is in [27.0, 44.0], and longitude is in [-18.5, 4.5]. The box covers the mainland, the Balearic and Canary Islands, Ceuta, and Melilla. A `KeyError`, a `ValueError`, or a value outside the box skips the entry with a warning that names `IDEESS`.

### The revision

The revision is a copy of `french_tolls/alembic/versions/2026-11-07_15-52_gas_stations.py` with the new columns. It has the R*Tree `gas_station_area` and the insert, update, and delete triggers, and the warning about batch copies.

`alembic/env.py` gets the same `include_object` filter as `french_tolls`. The filter stops autogenerate from proposing to drop the R*Tree tables.

### Fuel groups: `gasolinera/fuels.py`

```python
FUEL_GROUPS = {
    "gasoline_95": ("Precio Gasolina 95 E5", "Precio Gasolina 95 E10",
                    "Precio Gasolina 95 E5 Premium", "Precio Gasolina Renovable"),
    "gasoline_98": ("Precio Gasolina 98 E5", "Precio Gasolina 98 E10"),
    "diesel": ("Precio Gasoleo A", "Precio Gasoleo Premium", "Precio Diésel Renovable"),
}
```

`group_price(prices, group)` returns `(field, Decimal)` or `None`. It reads each field as `Decimal(text.replace(",", "."))`. It ignores a text that raises `InvalidOperation` or gives a non-finite value, because `Decimal("NaN")` parses. `min` over the group order with the price as the key keeps the first field on a tie.

`Decimal` gives the exact value of the text, so `"1,459"` compares as 1.459 and not as the nearest float.

The map uses the full field names, `Precio …`, so a lookup reads the stored object directly.

Alternative: store the group prices in columns. Rejected by the user. The map lives in the code, so a change to a group needs no migration.

### The run

`python3 -m gasolinera.gas_stations` takes no argument. `main()` sets up logging like the bot, runs `update()`, and exits with its status.

`docker-compose.yml` gets the service `gas-stations` (profile `gas-stations`, volume `cache`, depends on `migrate`). `migrate` gets the profile `gas-stations` too. `make gas-stations` runs `$(COMPOSE) --profile gas-stations run --rm --no-TTY --build gas-stations`.

### Tests

The tests use a store in `tmp_path`, migrated by Alembic, with `db.Session` replaced, as in `french_tolls/french_tolls/tests/test_gas_stations.py`. The triggers exist only in the revision, so a schema built from the models would test neither them nor the index.

The fixture `gasolinera/tests/miteco_sample.json` holds real entries of the 07/11/2026 feed: a normal station, a Canary Islands station, the `0,0` station 11988, and the swapped station 16268. The tests change copies of this fixture for the other cases.

`test_store.py` changes. A fresh store now has the station table and the index, and its version is the new revision.

## Risks / Trade-offs

- [MITECO renames a price field] → The raw object keeps the new name. The group misses that fuel until `FUEL_GROUPS` changes. The run logs no warning for this.
- [A bad feed with few entries deletes most stations] → Accept it for now. The run fails only on an empty list. A later change can add a minimum count.
- [The 12 MB body is held in memory] → Accept it. The peak is about 100 MB of Python objects.
- [A batch revision that copies `gas_station` drops the triggers] → The revision carries the same warning as in `french_tolls`.

## Migration Plan

`make gas-stations` runs `migrate` first, which adds the table to an existing store. To roll back, run `alembic downgrade -1` in the `migrate` container.
