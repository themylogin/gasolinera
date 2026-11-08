# Tasks

## 1. The picture

- [x] 1.1 Write `gauge/render.py` and add the `gauge-image` target to the `Makefile`, as `design.md` describes. Run `make gauge-image`. Verify that `gasolinera/assets/gauges.png` exists, shows three tiles of one size with no text, and belongs to the operator.
- [x] 1.2 Verify that `requirements.txt` names no image library and that the built app image contains `/app/gasolinera/assets/gauges.png`.

## 2. The car

- [x] 2.1 Add `gauge_steps` (Integer, not null, `server_default="16"`) to the `Car` model, and generate and fill the revision `car_gauge` in a container. Verify that `alembic check` reports no difference and that a car stored before the upgrade has 16 after it. Update the revision id in `gasolinera/tests/test_store.py`.
- [x] 2.2 Add `gauge_steps` to `CarParameters`, the step `gauge` with its photo reply, the `24`, `16`, and `12` buttons, the text-instead-of-button reply, `Indicador: <steps> secciones` in `describe`, and the `load_car` check.
- [x] 2.3 Update `gasolinera/tests/test_car.py` for the seven steps, the gauge buttons, the photo flag, the seven-line format, and `load_car` with an unknown gauge. Verify that `make test` passes.

## 3. The gauges

- [x] 3.1 Replace `GAUGE` with `GAUGES` and change `gauge_mark(step, steps)` in `gasolinera/journey.py`.
- [x] 3.2 Update `gasolinera/tests/test_journey.py` for the rows of the three gauges, the repeated row labels, and the marks `1`, `0`, `7/8`, `5/6`, and `13/16`. Write each expected value as a literal. Verify that `make test` passes.

## 4. The bot

- [x] 4.1 In `gasolinera/bot.py`, send the gauge question as a photo, edit a pressed photo's caption, build the fuel keyboard from the gauge of the car, and read a press with its steps.
- [x] 4.2 Add `sendPhoto` and `editMessageCaption` to the fake transport in `gasolinera/tests/telegram.py`. Update `gasolinera/tests/test_bot_flow.py`:
  - `enter_car` presses a gauge;
  - the gauge question is a photo with three buttons, and its caption changes after a press;
  - text instead of a gauge button;
  - the keyboard of each gauge;
  - `7/8` on the 24-step gauge;
  - `0`, with a station near the origin in the answer;
  - the old-button scenario on the gauge question.

  Verify that `make test` passes.

## 5. Documentation and live check

- [x] 5.1 Update the "Bot" section of `README.md` for the gauge question, and document `make gauge-image`. Verify that the target exists.
- [x] 5.2 Restart the bot with `make bot`, and ask the user to run `/coche` with each gauge, and one journey with a press on `0`. Mark this task only after the user confirms.
