# Proposal

## Why

A driver rarely knows how many liters are in the tank. They see a fuel gauge, and many cars also show the range in kilometers. The bot asks `¿Cuántos litros de combustible te quedan?` and waits for a number, which forces the driver to guess.

## What Changes

- The fuel question becomes `¿Cuánto combustible te queda? Elige en el indicador o escribe los kilómetros de autonomía.` with an inline keyboard shaped like a fuel gauge:
  - `[1/1][.][.][.][3/4]`
  - `[3/4][.][.][.][1/2]`
  - `[1/2][.][.][.][1/4]`
  - `[1/4][.][.][.]`

  Each button is a sixteenth of the tank, from 16/16 down to 1/16. Each row shows both ends of its quarter, so `3/4`, `1/2`, and `1/4` appear twice with one meaning.
- **A press on the gauge** gives the fuel as the tank volume × sixteenths / 16. The search then works as today, from the point where the tank holds 5 L.
- **A typed number is now the range in kilometers.** **BREAKING** for users who typed liters. It is not converted to fuel. The search point is the route point where the range drops to the reserve of the car. When the range lasts to the destination with the reserve left, no stop is needed.
- `/coche` gets a sixth question: the reserve in kilometers, `¿Con cuántos kilómetros de autonomía quieres repostar?`. Stored cars get 50 km.
- With a typed range, the stop buys the tank volume minus 5 L.
- After a failed route, the bot asks the fuel question again with a new gauge.
- A button from an older fuel question changes nothing.

Out of scope:

- An `E` (empty) button.
- Using the reserve for the gauge. The gauge keeps the 5 L rule.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `journey-dialog`: the fuel question, the gauge, a typed range instead of typed liters, the no-stop text for a range, the expired gauge, and the new question after a failed search.
- `refuel-search`: a search from a range in kilometers, its search point, its no-stop rule, and its stop liters.
- `car-parameters`: the sixth question, the reserve, and the shown format.

## Impact

- Code: `gasolinera/bot.py`, `gasolinera/journey.py`, `gasolinera/refuel.py`, `gasolinera/car.py`, `gasolinera/models.py`.
- A new Alembic revision adds `car.reserve_km` with the server default 50.
- Tests of the bot flow, the journey texts, the search, and the car dialog change.
