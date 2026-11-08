# Proposal

## Why

Sometimes a driver needs fuel now and has no destination in mind. Today the bot always asks for a destination and plans a route. The driver cannot see the stations around them.

## What Changes

- The message `Ahora envíame el destino.` gets one inline button: `o mostrar gasolineras cercanas`.
- A press lists the 10 stations nearest to the origin that sell the fuel group of the car, nearest first. The distance is the straight-line distance. No route is requested.
- Each station shows its name as a Google Maps link, its distance in km with one decimal, and its price. An alert line follows when the station is closed, closes soon, or has an unknown schedule now.
- The list ends the journey. The next location is a new origin.
- The button expires when the user sends a destination, sends a new origin, or sends `/reiniciar`.

Assumptions:

- "Nearby" means within 50 km, as for the refuel search. With no station in that radius, the bot says so.
- The list has 10 stations, as the refuel answer has.
- A press removes the button and keeps the text `Ahora envíame el destino.`

Out of scope:

- Road distance or driving time to each station.
- A sort by price or by cost.
- A change to the `/info` text.

## Capabilities

### New Capabilities

- `nearby-stations`: the list of the stations nearest to a position, its order, its size, and its format.

### Modified Capabilities

- `journey-dialog`: the button on the destination question, its press, and its expiry.

## Impact

- Code: `gasolinera/bot.py` (the button, its token, and its handler), `gasolinera/refuel.py` (the nearby list, built on `candidates`), and `gasolinera/journey.py` (the format).
- Tests: `gasolinera/tests/test_refuel.py`, `gasolinera/tests/test_journey.py`, and `gasolinera/tests/test_bot_flow.py`.
- `README.md`: the button in the "Bot" section.
- No new setting, no new service, no schema change.
