# Tasks

## 1. The reserve

- [x] 1.1 Add `reserve_km` (Float, not null, `server_default="50"`) to the `Car` model, and generate and fill the revision `car_reserve` in a container. Verify that `alembic check` reports no difference, that `down_revision` is `f82ef6e766d8`, and that a car row stored before the upgrade has 50 after it.
- [x] 1.2 Update `gasolinera/tests/test_store.py` with the new revision id as a literal. Verify that `make test` passes.
- [x] 1.3 Add `reserve_km` to `CarParameters`, add the step `reserve_km` and `parse_reserve_km` to `gasolinera/car.py`, move the save to that step, and add `Reserva: <value> km` to `describe`.
- [x] 1.4 Update `gasolinera/tests/test_car.py` for the six steps, the reserve checks, the six-line format, and `load_car` and `save_car` with the reserve. Verify that `make test` passes.

## 2. The search from a range

- [x] 2.1 Add `range_walk`, change `NoStop` to carry `fuel_left` or `range_left`, and change `refuel.search` to take `liters` or `range_km` after `*`, as `design.md` describes.
- [x] 2.2 Update `gasolinera/tests/test_refuel.py`: each new `refuel-search` scenario, both stop-liter rules, and `ValueError` for both inputs or neither. Verify that `make test` passes.

## 3. The gauge and the texts

- [x] 3.1 Add `GAUGE`, `gauge_mark`, and `parse_range` to `gasolinera/journey.py`, remove `parse_liters` and `liters_error`, and give `format_answer` the range text.
- [x] 3.2 Update `gasolinera/tests/test_journey.py`: the gauge rows, `gauge_mark` for 16, 12, 13, and 1, `parse_range` from 0 to 3000 with a comma, and the two no-stop texts. Write each expected text as a literal. Verify that `make test` passes.

## 4. The bot

- [x] 4.1 In `gasolinera/bot.py`, add `gauge_token` to `Journey`, `ChatState.new_gauge_token`, `ask_fuel`, the typed range, `gauge_button_handler` on `^gauge:`, and the new question after `RouterUnavailable`.
- [x] 4.2 Update `gasolinera/tests/test_bot_flow.py`. Cover each new or changed `journey-dialog` scenario:
  - the keyboard rows;
  - a press on each `3/4`;
  - the pressed text for `1/2` and for 13/16;
  - a typed range;
  - text that is not a range;
  - an old gauge, and a gauge after `/reiniciar`;
  - the new gauge after a router failure.

  Update `enter_car` for the reserve question. Verify that `make test` passes.

## 5. Documentation and live check

- [x] 5.1 Update the "Bot" section of `README.md` for the gauge, the typed range, and the reserve. Verify that it names no typed liters.
- [ ] 5.2 Restart the bot with `make bot`. Then, with `TELEGRAM_BOT_TOKEN` in `.env`, ask the user to run `/coche` with a reserve, one journey with a gauge press, and one with a typed range. Mark this task only after the user confirms both answers.
