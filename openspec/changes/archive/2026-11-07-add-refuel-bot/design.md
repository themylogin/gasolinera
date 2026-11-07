# Design

## Context

The `gasolinera` code today:
- **`bot.py`** builds an `Application` with no handler.
- **`gas_stations.py`** fills `gas_station` and gives `stations_in_area`.
- **`fuels.py`** gives `FUEL_GROUPS` and `group_price`.
- **`config.py`** has `telegram_bot_token` and `log_level`.
- **`osrm`** runs on the Compose network. Nothing calls it yet.

`french_tolls` has the parts this change copies:
- **`car.py`:** a pure dialog (`CarDialog`, `CarReply`, `start`, `answer_text`, `answer_button`), plus `load_car` and `save_car`. `bot.py` keeps the open dialogs in `ChatState.car_dialogs` and turns a `CarReply` into a message with inline buttons.
- **`refuel.py`:** `consumption_at`, `fuel_walk`, `candidates`, `detours`, and `plan`.
- **`osrm.py`:** `Routers` with `aiohttp`, snapping, budgets, and toll graphs. Most of this does not apply here.
- **`integration/telegram_transport.py` and `integration/chat.py`:** a fake `BaseRequest` that answers the Bot API from written payloads, and a `Chat` driver that sends updates through the real `Application`.

From the `Horario` texts of the 07/11/2026 feed:
- They have 1,175 distinct values. 99.8% of the stations match `<days>: <24H | HH:MM-HH:MM>[; …]`.
- The other 23 stations differ only by a one-digit hour (`7:00`) or a space before the dash.
- `y` joins two ranges in one day.
- 263 stations have ranges that end at or after midnight, such as `06:00-00:00` and `06:00-02:00`.
- 490 stations list only `L`.

The app image has `/usr/share/zoneinfo`, so `zoneinfo.ZoneInfo("Europe/Madrid")` and `ZoneInfo("Atlantic/Canary")` work with no new package.

## Goals / Non-Goals

**Goals:**

- Modules with pure logic that tests can call without Telegram, without OSRM, and without a store.
- One thin `bot.py` that connects them.
- The same structure as `french_tolls`, so that a fix can move between the two.

**Non-Goals:**

- Keeping the journeys after a restart. They live in memory, as in `french_tolls`.
- A query budget, request caching, or a remote router.
- A correction factor for OSRM travel times.

## Decisions

### Modules

| Module | Holds | Pure |
| --- | --- | --- |
| `osrm.py` | `Router(base_url, transport=None)`, `Route`, `NoRoute`, `RouterUnavailable` | no (HTTP) |
| `car.py` | `FUEL_LABELS`, the dialog functions, `parse_tank_volume`, `parse_consumption`, `parse_eur_per_hour`, `describe`, `load_car`, `save_car` | dialog yes, store no |
| `opening_hours.py` | `parse`, `state_at`, `OpeningState` | yes |
| `refuel.py` | `consumption_at`, `fuel_walk`, `candidates`, `stop_cost`, `search`, `NoStop`, `Stops`, `Listed`, `station_zone`, `station_link` | no (router, store) |
| `journey.py` | `parse_location`, `parse_liters`, `format_answer`, `INFO`, and the fixed Spanish texts | yes |
| `bot.py` | `ChatState`, the handlers, `post_init`, `build`, `main` | no |

`car.FUEL_LABELS` maps the keys of `fuels.FUEL_GROUPS` to `Gasolina 95`, `Gasolina 98`, `Diésel`. A test checks that the two sets of keys are equal, so a new group cannot lack a label.

### The OSRM client

The client uses `httpx.AsyncClient` with a timeout of 30 s, the same as the `gas-stations` run. It has two calls:

- `distance_to_road(location)` calls `/nearest/v1/driving/<lon>,<lat>?number=1` and returns the `distance` of the first waypoint. With no waypoint, it returns infinity.
- `route(points, *, segments=False)` calls `/route/v1/driving/<points>` with `overview=false` and `steps=false`. With `segments=True` it adds `annotations=distance,duration`, `overview=full`, and `geometries=geojson`. It returns `Route(distance, duration, leg_distance, leg_duration, coordinates, segment_distance, segment_duration)`.

The code `NoRoute` or `NoSegment` raises `NoRoute`. Any other code, a body that is not JSON, or an `httpx.HTTPError` raises `RouterUnavailable`. With `segments=True`, a route whose number of coordinates is not one more than its number of segments also raises `RouterUnavailable`.

The planned route has one leg. A detour has two legs, and the search needs only their totals, so it requests no annotation.

Alternative: copy `french_tolls/osrm.py`. Rejected. Hints, matching, budgets, and two graphs serve the toll search, and `aiohttp` would be a new package.

`config.time_multiplier` reads `TIME_MULTIPLIER`, with the default `0.933`. The search multiplies every router duration by it: the segment durations, the planned route, and both legs of a detour. The client returns the raw durations, so a test of the client does not depend on the setting. `french_tolls` measured 0.9333 against Google on French roads, and the same value is the starting point for Spain.

### The car dialog

The dialog is the dialog of `french_tolls/car.py` with these changes:
- The second speed is 120 km/h.
- A fifth step asks the value of time in €/h. `french_tolls` reads it from the setting `EUR_PER_HOUR` instead.
- All texts are in Spanish.
- Consumptions and the value of time take a comma.

The step order is `confirm` (only for a user with a car), then `tank_volume`, `fuel_type`, `consume_80`, `consume_120`, `eur_per_hour`. `parse_tank_volume` is the `french_tolls` one: up to 18 digits, so the value fits the SQLite integer, and 30 or more. Buttons carry `car:<token>:<choice>`. The token comes from `ChatState.new_car_token()`, so an old button does not match the open dialog.

`describe` prints the five lines. It prints a value with `f"{value:.6f}".rstrip("0").rstrip(".")` and then replaces `.` with `,`. This is the same rounding as `french_tolls`.

### The car table

| Column | Type |
| --- | --- |
| `telegram_user_id` | Integer, primary key, no autoincrement |
| `tank_volume` | Integer |
| `fuel_type` | Text, a key of `FUEL_GROUPS` |
| `consume_80` | Float |
| `consume_120` | Float |
| `eur_per_hour` | Float |

`save_car` upserts with `on_conflict_do_update`, as in `french_tolls`. `load_car` returns `None` when the row is missing or its `fuel_type` is no longer a group key. A removed group then makes the user run `/coche` again, and the search cannot fail on a key error.

### The journey state

`ChatState` holds:
- `journeys: dict[user_id, Journey]`, where `Journey(origin, destination=None)` is a frozen dataclass;
- `car_dialogs: dict[user_id, CarDialog]`;
- a token counter.

The message handler routes in this order:

1. A Telegram location goes to the journey.
2. With an open car dialog, typed text goes to `car.answer_text`.
3. With an open fuel question (`journey.destination` is set), typed text goes to `parse_liters`. On failure the bot sends the liters error. `12,5` must be read as liters and not as the coordinates `12, 5`.
4. Typed text that `parse_location` reads goes to the journey.
5. Any other text gets `journey.INFO`.

A location goes through these checks:
- First, `router.distance_to_road(location)`. More than 1,000 m gives the refusal.
- Without a journey, or with a full one, the bot loads the car. With no car, it sends `Primero dime…`. With a car, it keeps `Journey(origin)`.
- With an origin only, it keeps the destination and asks for the liters.

`parse_location` uses the `french_tolls` pattern, `(?<![\d.])(-?\d+(?:\.\d+)?)(?![\d.])`, twice with a comma between. It returns `(longitude, latitude)`.

`parse_liters(text, tank_volume)` accepts `\s*\d+([.,]\d+)?\s*` from 0 to the tank volume. The bot loads the car again when the liters arrive, so a `/coche` change made during the journey applies.

### The search

`refuel.search(router, origin, destination, car, liters, now)` follows `french_tolls/refuel.plan` without tolls. `m` below is `config.time_multiplier`.

1. `route = await router.route([origin, destination], segments=True)`.
2. `fuel_walk` gives the search index and the fuel left, with `consumption_at` on the 80/120 curve and the speed `distance / (duration × m) × 3.6`.
3. No search index gives `NoStop(fuel_left)`. Otherwise the stop buys `stop_liters = car.tank_volume - fuel_left`.
4. `candidates` calls `gas_stations.stations_in_area` on a box of ±50 km around the search point. It keeps the stations where `group_price(station.prices, car.fuel_type)` is not `None` and the great-circle distance is at most 50 km. It sorts them by distance and then id, and keeps 30.
5. A detour is `router.route([origin, station, destination])` under `asyncio.Semaphore(4)`. `NoRoute` drops the candidate. `RouterUnavailable` stops the search.
6. Each result becomes `Listed(station, field, price, distance_m=leg_distance[0], detour_s=(duration - route.duration) × m, arrival=now + leg_duration[0] × m, cost, state)`, where `cost = stop_cost(stop_liters, price, detour_s, car.eur_per_hour) = stop_liters × price + detour_s / 3600 × eur_per_hour`.
7. The results are sorted by `(cost, station.id)`, and the first 10 are kept in `Stops(liters=stop_liters, stations=...)`.

`now` is a parameter, so a test fixes the clock. The bot passes `datetime.now(timezone.utc)`.

`station_zone(province)` returns `ZoneInfo("Atlantic/Canary")` for `PALMAS (LAS)` and `SANTA CRUZ DE TENERIFE`, and `ZoneInfo("Europe/Madrid")` for every other province. Ceuta and Melilla share the Madrid offset.

### Opening hours

`parse(text)` returns a sorted list of open intervals, in minutes from Monday 00:00. The week has 10,080 minutes. The function returns `None` for unknown. It works in four steps:

1. Split on `;`. Match each part with `^\s*(?P<days>[LMXJVSD](\s*-\s*[LMXJVSD])?(\s*,\s*[LMXJVSD](\s*-\s*[LMXJVSD])?)*)\s*:\s*(?P<times>.+?)\s*$`.
2. Read `<times>` as `24H`, or as ranges split on `\s+y\s+`, each `(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})`. Hours run 0 to 23, and minutes 0 to 59. `23:59` as an end becomes 24:00.
3. Make an interval for each named day. An end at or before its start adds 24 h.
4. Normalise the intervals to the week: a part past 10,080 wraps to the start. Then merge overlapping or touching intervals. When the intervals cover the whole week, the result is the single interval `(0, 10080)`, marked as always open.

The schedule is `None` when the days of all parts together are `{L}`.

`state_at(text, local)` turns `local` into a week minute. It finds the interval that holds it, and checks a wrapped interval across the end of the week.

- No interval gives `closed`.
- An always-open schedule gives `open`.
- When `end - minute < 20`, the state is `closing_soon`, with `closes_at = local + (end - minute) minutes`.
- Otherwise the state is `open`.

The arrival is a time of day, and the schedule has no dates, so the week-minute model is exact. The only exception is the night of a DST change, and this change accepts that.

### The answer text

`journey.format_answer(answer, fuel_label)` returns the HTML text. It builds it with `html.escape`. Prices use `f"{price:.3f}".replace(".", ",")`. The distance is `round(distance_m / 1000)`, and the detour is `round(detour_s / 60)` with a `+` sign when it is 0 or more. The bot sends the text with `parse_mode="HTML"` and `link_preview_options=LinkPreviewOptions(is_disabled=True)`.

### Bot construction

`build(token, *, request=None, get_updates_request=None, router=None)`. With no `router`, it builds `Router(config.osrm_url)`. Tests pass a router on an `httpx.MockTransport` and the fake Telegram request. `post_init` sets the menu.

`/info` and `/start` send `journey.INFO`, and neither changes the journey or a car dialog. Telegram sends `/start` on the first contact, and without it a new user gets nothing. `INFO` holds the usage, the commands, and the two tip links of the `french_tolls` bot, in Spanish.

### Tests

- **`gasolinera/tests/conftest.py`:** holds the migrated `tmp_path` store fixture, moved from `test_gas_stations.py`, so the car, refuel, and bot tests share it.
- **`gasolinera/tests/telegram.py`:** a copy of `french_tolls/french_tolls/integration/telegram_transport.py` and the needed part of `chat.py`. The Spanish button labels are written in the test, not imported.
- **Pure tests:** `test_car.py`, `test_opening_hours.py`, `test_journey.py`, `test_osrm.py`, and `test_refuel.py`. `test_refuel.py` uses a stub router class and stations inserted into the store.
- **`test_bot_flow.py`:** whole conversations through the real `Application`: the car dialog, the journey, `/reiniciar`, the refusals, and the errors.
- **`test_store.py`:** the table list gets `car`, and the version becomes the new revision.

## Risks / Trade-offs

- [A full tank can be more fuel than the user wants to buy] → The same as `french_tolls`. Every candidate of one search buys the same liters, so the rule only sets how much a cent per liter weighs against a minute of detour.
- [Candidates near the search point can lie past the point where the tank is empty] → The same as `french_tolls`. The 5 L reserve and the 50 km radius keep most of them reachable.
- [OSRM durations differ from real driving] → The arrival time can be wrong by some minutes. The 20-minute warning absorbs some of it.
- [A wrong `Horario` gives a wrong alert] → The bot shows the alert, not a decision, and an unknown schedule shows its text.
- [Journeys are lost when the bot restarts] → The user sends the locations again. `/coche` data is in the store.
- [Up to 32 routing requests for one answer] → `osrm` is local, and the search takes about 1 s on the Spain graph.

## Migration Plan

`make bot` runs `migrate`, which adds `car`. To roll back, run `alembic downgrade -1` and deploy the previous image.
