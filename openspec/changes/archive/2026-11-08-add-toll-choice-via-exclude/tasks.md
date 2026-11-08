# Tasks

## 1. The toll-free router

- [x] 1.1 In `gasolinera/osrm.py`, add `exclude=None` to `Router.__init__`. When it is set, `route` adds `exclude=<value>` to its query, with and without segments. `distance_to_road` does not add it. In `gasolinera/tests/test_osrm.py`, add tests for:
  - `exclude="toll"`: the route query has `exclude=toll`, and the nearest query has no `exclude`;
  - no `exclude`: the route query has no `exclude` key.

  Verify that `make test` passes.

## 2. The toll question in the bot

- [x] 2.1 In `gasolinera/bot.py`, store the toll-free router in `build` under a second `bot_data` key, made as `Router(router.base_url, router.transport, exclude="toll")`. Add the `Journey` fields `toll_token`, `toll_minutes`, and `avoid_tolls`, and `ChatState.new_toll_token`. Verify that `make test` passes with no change to the existing tests.
- [x] 2.2 Add `choose_route` as `design.md` describes, and call it from `handle_location` after the car check of the destination. Send the toll question with the buttons `Sí (-<minutes> min)` and `No`. Verify with `make test` that only the two route-count assertions fail: `test_a_gauge_after_reiniciar` and `test_a_second_press_on_one_gauge`.
- [x] 2.3 Update those two assertions for the two route requests of the destination step: 0 becomes 2, and 1 becomes 3. Verify that `make test` passes.
- [x] 2.4 Add `toll_button_handler` on `^tolls:`. In `message_handler`, check the toll question before the range: typed coordinates go to `handle_location`, other text goes to `send_info`. In `handle_range` and `gauge_button_handler`, pick the router of the search from `journey.avoid_tolls`. Verify that `make test` passes.
- [x] 2.5 In `gasolinera/tests/test_bot_flow.py`, add the fields `tolls_s` and `toll_free` to the fake `Osrm` as `design.md` describes. Verify that every existing flow test passes with no change to its assertions.
- [x] 2.6 Add one flow test for each scenario of the `journey-dialog` and `refuel-search` deltas, except the two live scenarios with city coordinates:
  - same routes: no toll question, and no search request has `exclude`;
  - 7,400 s and 10,201 s: `¿Quieres usar autopistas de peaje?` with `Sí (-44 min)` and `No` in one row;
  - 7,400 s and 12,224 s: `Sí (-75 min)`;
  - 7,400 s and 7,420 s: no toll question, and every search request has `exclude=toll`;
  - `Sí (-44 min)` and `1/2`: the question becomes `Peajes: Sí (-44 min)`, then the fuel question, and no search request has `exclude`;
  - `No` and `1/2`: the question becomes `Peajes: No`, and the planned route and every detour have `exclude=toll`;
  - `No`, a failed search, and `1/2` on the new gauge: every request of the second search has `exclude=toll`;
  - toll-free `down` or `no_route`: no toll question, and no search request has `exclude`;
  - `planned = "down"` at the destination: `No he podido calcular la ruta. Lo siento mucho 😞`, and the next location is the destination;
  - `planned = "no_route"` at the destination: the no-road text, and the next location is an origin;
  - a shared location and typed `40.4168, -3.7038` during the toll question: `Ahora envíame el destino.`;
  - `hola` during the toll question: the info text, and `No` still sends the fuel question;
  - a second press, and a press after `/reiniciar`: `Esta pregunta ha caducado.`

  Write each expected text as a literal. Verify that `make test` passes.
- [x] 2.7 Update the "Bot" section of `README.md`: after the destination, the bot asks about tolls when the toll-free route differs, and shows the time that the tolls save. Verify that the button labels in the README match the labels in the tests.

## 3. Live check

- [x] 3.1 From a container on the Compose network, request Barcelona `2.1734,41.3851` to Lleida `0.6200,41.6176` and to Puigcerdà `1.9280,42.4317` from `http://osrm:5000`, with and without `exclude=toll`. Verify that all four answers are `Ok`, that the Lleida geometries are equal, and that the Puigcerdà toll-free duration is longer.
- [ ] 3.2 Restart the bot with `make bot`. Ask the user to send one journey from Barcelona to Lleida and one from Barcelona to Puigcerdà. Mark this task only after the user confirms that Lleida shows no toll question and Puigcerdà shows `Sí (-<minutes> min)` and `No`.

## Workflow follow-up

- Delete the change `add-toll-route-choice`, or archive it with `--skip-specs`, so that its deltas do not reach the main specs.
