# Tasks

## 1. Shared test setup

- [x] 1.1 Move the migrated `tmp_path` store fixture from `gasolinera/tests/test_gas_stations.py` to `gasolinera/tests/conftest.py`. Verify that `make test` still passes with the same test count.

## 2. OSRM client

- [x] 2.1 Add `osrm_url` (default `http://osrm:5000`) and `time_multiplier` (default `0.933`) to `gasolinera/config.py`, and `OSRM_URL` and `TIME_MULTIPLIER` with a comment each to `.env.example`. Verify that both defaults apply with no `.env`.
- [x] 2.2 Create `gasolinera/osrm.py` with `Router`, `Route`, `NoRoute`, and `RouterUnavailable`, as `design.md` describes.
- [x] 2.3 Write `gasolinera/tests/test_osrm.py` with `httpx.MockTransport`. Cover the request URL and parameters of each call, the distance of `/nearest`, a route with segments, a two-leg route, `NoRoute` for `NoRoute` and `NoSegment`, and `RouterUnavailable` for another code, for HTML, for a connection error, and for a segment count mismatch. Verify that `make test` passes.

## 3. Opening hours

- [x] 3.1 Create `gasolinera/opening_hours.py` with `parse`, `state_at`, and `OpeningState`.
- [x] 3.2 Write `gasolinera/tests/test_opening_hours.py` with one test for each `opening-hours` scenario, and with a wrap from Sunday night to Monday morning. Verify that `make test` passes.
- [x] 3.3 Run `parse` on every `Horario` of a live MITECO fetch. Verify that only the Monday-only schedules and texts outside the grammar give `None`, and report their counts.

## 4. Car parameters

- [x] 4.1 Add the `Car` model to `gasolinera/models.py`, and generate and fill the revision `car` in a container. Verify that `alembic check` reports no difference, and that `down_revision` is `255cb2d4557a`.
- [x] 4.2 Update `gasolinera/tests/test_store.py` with the `car` table and the new revision id, as literals. Verify that `make test` passes.
- [x] 4.3 Create `gasolinera/car.py` with `FUEL_LABELS`, `CarParameters`, `CarDialog`, `CarReply`, `start`, `answer_text`, `answer_button`, `parse_tank_volume`, `parse_consumption`, `parse_eur_per_hour`, `describe`, `load_car`, and `save_car`.
- [x] 4.4 Write `gasolinera/tests/test_car.py` for the pure dialog with its five steps, the tank volume, consumption, and value of time checks, `describe`, the key match between `FUEL_LABELS` and `FUEL_GROUPS`, and `load_car`/`save_car` on the store fixture, with a row whose group is unknown. Verify that `make test` passes.

## 5. Refuel search

- [x] 5.1 Create `gasolinera/refuel.py` with `consumption_at`, `fuel_walk`, `candidates`, `stop_cost`, `search`, `NoStop`, `Stops`, `Listed`, `station_zone`, and `station_link`.
- [x] 5.2 Write `gasolinera/tests/test_refuel.py` with a stub router and stations in the store fixture. Cover each `refuel-search` scenario, including the `TIME_MULTIPLIER` correction of speed, detour, and arrival, the stop liters, the cost order, at most four open detours, the arrival times, and both time zones. Verify that `make test` passes.

## 6. Journey texts

- [x] 6.1 Create `gasolinera/journey.py` with `parse_location`, `parse_liters`, `format_answer`, `INFO`, and the fixed texts of `journey-dialog`.
- [x] 6.2 Write `gasolinera/tests/test_journey.py` for the parsers with the tank volume limit, the whole `INFO` text, the three answer forms with the liters in the header, each alert line, the escaping, the empty name, and the detour sign. Write each expected text as a literal. Verify that `make test` passes.

## 7. Bot

- [x] 7.1 Copy the fake Telegram transport and the chat driver from `french_tolls/french_tolls/integration/` to `gasolinera/tests/telegram.py`, reduced to the calls this bot makes.
- [x] 7.2 Rewrite `gasolinera/bot.py` with `ChatState`, the handlers, `post_init`, and `build(token, *, request=None, get_updates_request=None, router=None)`, as `design.md` describes. Keep `main` and its token check.
- [x] 7.3 Replace the "no handlers" test in `gasolinera/tests/test_bot.py` with the menu test. Write `gasolinera/tests/test_bot_flow.py`, which drives the real `Application` through the fake transport, with a router on `httpx.MockTransport` and stations in the store fixture. Cover each scenario of `car-parameters` and `journey-dialog` that needs Telegram, `/info`, and `/start`. Verify that `make test` passes.

## 8. Documentation

- [x] 8.1 Add a "Bot" section to `README.md`: `/coche`, the journey, `/reiniciar`, `/info`, `TIME_MULTIPLIER`, and the need for `make osrm` and `make gas-stations` before `make bot`. Verify that every command in it exists.
- [x] 8.2 Change the `## Purpose` of `openspec/specs/telegram-bot/spec.md` to say that the bot runs the car dialog and the refuel journey. Verify that `openspec validate --specs --strict` passes.

## 9. Integration checks

- [x] 9.1 With `make osrm` running and a fresh `make gas-stations`, run `refuel.search` in the bot image for Madrid (40.4168, -3.7038) to Barcelona (41.3874, 2.1686), a `diesel` car with a 60 L tank, 6 and 7.5 L/100 km, and 20 €/h, and 15 L. Verify that it returns 10 stations ordered by cost, with distances between 0 and 630 km, and print `format_answer` for review.
- [x] 9.2 Run the same search with 60 L. Verify that it gives `NoStop`. The graph has no Canary Islands, because Geofabrik lists them outside its Spain extract, so a live route on Tenerife cannot run. The unit tests alone cover `Atlantic/Canary`. Verify that the README states this limit.
- [x] 9.3 Run `make bot` with a valid `TELEGRAM_BOT_TOKEN` if one is available. Verify the `/coche` dialog and one journey by hand. If no token is available, report that and do not mark this task.
