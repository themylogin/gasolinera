# Tasks

## 1. The nearby list

- [x] 1.1 In `gasolinera/refuel.py`, add the `Nearby` dataclass and `nearby(position, fuel_type, now)` as `design.md` describes. In `gasolinera/tests/test_refuel.py`, add tests:
  - 12 stations that sell diesel: `nearby` keeps the 10 nearest, nearest first;
  - two stations at the same distance: the lower id comes first;
  - a station in `MADRID` with `L-D: 07:00-22:00` and `now` at 21:41 UTC on 2026-11-07: the state is `closed`, and `local_time` is 22:41.

  Verify that `make test` passes.

## 2. The format

- [x] 2.1 In `gasolinera/journey.py`, move the link, name, price, and alert code of `_station_lines` into helpers that take plain values. Verify that every existing test in `gasolinera/tests/test_journey.py` passes with no change.
- [x] 2.2 Add `format_nearby(stations, fuel_label)`. In `gasolinera/tests/test_journey.py`, add one test for each scenario of the `nearby-stations` delta that is about text: the two lines of `GALP` at 430 m, `· 12,5 km`, `⚠️ <b>Cerrada</b> a las 22:41`, `⚠️ <b>Cierra pronto</b> a las 22:00`, `⚠️ <b>Horario desconocido</b>`, the escaped name, the numbering with empty lines, and `Ninguna gasolinera vende Diésel a menos de 50 km de tu ubicación.` Write each expected text as a literal. Verify that `make test` passes.

## 3. The button in the bot

- [x] 3.1 In `gasolinera/bot.py`, add `Journey.nearby_token`, `ChatState.new_nearby_token`, and the button `o mostrar gasolineras cercanas` with callback data `nearby:<token>` on `Ahora envíame el destino.` Verify that `make test` passes with no change to the existing tests.
- [x] 3.2 Add `nearby_button_handler` on `^nearby:` as `design.md` describes. In `gasolinera/tests/test_bot_flow.py`, add flow tests:
  - after the origin, `Ahora envíame el destino.` has one row with the one button `o mostrar gasolineras cercanas`;
  - a press with a station at the origin: the text `Ahora envíame el destino.` stays, its button is gone, and the last message is the list with `parse_mode` `HTML` and no link preview;
  - no route request is made by the press;
  - a press and then a location: `Ahora envíame el destino.`;
  - a press after the destination: `Esta pregunta ha caducado.`, and the fuel question still works;
  - a press on the first message after a new origin: `Esta pregunta ha caducado.`, and the second button still sends the list;
  - a press after `/reiniciar`: `Esta pregunta ha caducado.`, and no list;
  - two presses on one message: one list, then `Esta pregunta ha caducado.`;
  - no station: `Ninguna gasolinera vende Diésel a menos de 50 km de tu ubicación.`

  Write each expected text as a literal. Verify that `make test` passes.
- [x] 3.3 Update the "Bot" section of `README.md`: after the origin, the button `o mostrar gasolineras cercanas` lists the 10 nearest stations that sell your fuel, by straight-line distance. Verify that the button label in the README matches the label in the tests.

## 4. Live check

- [ ] 4.1 Restart the bot with `make bot`. Ask the user to send a location and press `o mostrar gasolineras cercanas`. Mark this task only after the user confirms that the list shows the nearest stations first.
