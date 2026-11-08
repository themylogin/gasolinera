# Design

## Context

Today the journey works like this:
- `bot.handle_location` keeps `Journey(origin, destination)`, and then sends the fuel question as plain text.
- `bot.handle_liters` reads typed liters with `journey.parse_liters` and calls `refuel.search(router, origin, destination, parameters, liters, now)`.
- `refuel.search` walks the route with `fuel_walk` and fills the tank with `tank_volume - fuel_left`.
- The `/coche` dialog already uses inline buttons, with `car:<token>:<choice>` callback data and a token from `ChatState`, so an old button does not match. The gauge reuses that pattern.

## Goals / Non-Goals

**Goals:**

- One search function that takes either liters or a range.
- The gauge follows the same expiry rules as the `/coche` buttons.

**Non-Goals:**

- Converting a range to liters. The user rejected it.
- Keeping the typed liters. A typed number is now a range.

## Decisions

### The gauge keyboard

`journey.GAUGE` is the layout as data: four rows of `(label, sixteenths)`:

```python
GAUGE = (
    (("1/1", 16), (".", 15), (".", 14), (".", 13), ("3/4", 12)),
    (("3/4", 12), (".", 11), (".", 10), (".", 9), ("1/2", 8)),
    (("1/2", 8), (".", 7), (".", 6), (".", 5), ("1/4", 4)),
    (("1/4", 4), (".", 3), (".", 2), (".", 1)),
)
```

A button carries `gauge:<token>:<sixteenths>`. Telegram needs unique callback data only per press, not per keyboard, so the two `3/4` buttons may share one value.

`journey.gauge_mark(sixteenths)` returns the label of the first button with that value when the label is not `.`, and `<n>/16` otherwise. So 12 gives `3/4`, and 13 gives `13/16`.

### The journey state

`Journey` gets `gauge_token: str | None = None`. `handle_location` sets it with `ChatState.new_gauge_token()` (`g<n>`) when it keeps the destination. A failed search sets a new one when it asks again.

`gauge_button_handler` handles `^gauge:`. A press is valid when the user has a journey with a destination and the same `gauge_token`.
- **Valid press:** the bot edits the question into `Combustible: <mark> (<liters> L)` and starts the search with `liters = tank_volume × n / 16`.
- **Any other press:** the bot removes the buttons of that message and sends `Esta pregunta ha caducado.`

The text handler routes an open fuel question to `journey.parse_range`. The pattern is `\s*\d+([.,]\d+)?\s*`, from 0 to 3000.

### One search, two inputs

`refuel.search(router, origin, destination, parameters, now, *, liters=None, range_km=None)` takes exactly one of the two.

- **With `liters`:** today's `fuel_walk`, `NoStop(fuel_left=…)`, and `stop_liters = tank_volume - fuel_left`.
- **With `range_km`:** a new `range_walk(route, range_km, reserve_km)`. It subtracts `segment_distance / 1000` from the range, segment by segment, and returns the first index where the range left is `reserve_km` or less, or `None` with the range left at the end. `None` gives `NoStop(range_left=…)`. Otherwise `stop_liters = tank_volume - 5`.

`NoStop` gets two optional fields, `fuel_left` and `range_left`. `journey.format_answer` picks the text by which field is set.

`search` moves `liters` behind `*`, so every caller changes, and a call with both inputs or neither raises `ValueError`.

### The reserve

- `CarParameters` and the `car` model get `reserve_km: float`.
- The new revision adds `reserve_km` as `Float NOT NULL` with `server_default="50"`. SQLite fills the existing rows from the default. The model also declares `server_default="50"`, so `alembic check` stays clean.
- The dialog gets the step `reserve_km` after `eur_per_hour`, and saving moves to that step. `parse_reserve_km` uses the same decimal pattern, from 0 to 500.
- `describe` adds `Reserva: <value> km`.

### After a failed search

In `bot`, one helper `ask_fuel(message, state, user_id, journey)` sends the question with a new token and gauge. `handle_location` and the `RouterUnavailable` branch of the search both call it.

## Risks / Trade-offs

- [A user who typed liters now gets a range] → The question text says `kilómetros de autonomía`, so the change is visible. A liters number below 3000 is read as kilometers. For example, `30` gives a very early stop.
- [With a range, the stop liters are a guess] → Every candidate of one search buys the same liters, so only the weight of price against time changes. The design for `add-refuel-bot` explains this.
- [A tank under 40 L] → The `1/16` and `2/16` marks are 5 L or less, so the stop is planned at the origin. This is correct for a nearly empty tank.

## Migration Plan

`make bot` runs `migrate`, which adds `reserve_km` with 50 km to every stored car. To roll back, run `alembic downgrade -1` and deploy the previous image.
