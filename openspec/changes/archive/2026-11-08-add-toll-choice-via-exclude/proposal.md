# Proposal

## Why

The bot always plans the fastest route. In Catalonia that route often uses toll roads, for example the C-16 and the Cadí tunnel to Puigcerdà. Some drivers do not want to pay a toll when the saving is small. Today the bot does not tell them the saving, so they cannot choose.

## What Changes

- When the user sends the destination, the bot asks `osrm` for two routes: the normal route and the route with `exclude=toll`.
- When the two routes are the same, the bot asks the fuel question at once, as today. Example: Barcelona – Lleida.
- When the two routes differ, the bot asks `¿Quieres usar autopistas de peaje?` with two buttons: `Sí (-<minutes> min)` and `No`. Example: Barcelona – Puigcerdà, where the tolls save 44 min.
- `<minutes>` is the time that the tolls save, after `TIME_MULTIPLIER`, in whole minutes.
- After a press, the bot asks the fuel question. The refuel search and every detour then use the chosen route type.
- No second graph and no second service. The default `car.lua` already declares `toll` as an excludable class, and the MLD graph accepts `exclude=toll`. The running graph returned both routes for both examples.

Assumptions:

- When the routes differ but the tolls save less than half a minute, the bot sends no toll question. The search then uses the toll-free route.
- When the toll-free request fails, the bot sends no toll question and uses the normal route.
- The minutes stay in minutes above one hour, for example `-75 min`.

Out of scope:

- Toll prices. The question shows only the time.
- A stored preference. The bot asks on each journey where the routes differ.
- Reuse of the destination route in the search. The search requests its route again.

Overlap: the open change `add-toll-route-choice` gives the same dialog with a second graph and a second service `osrm-no-tolls`. Only one of the two changes must be applied. Archive or delete the other one.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `journey-dialog`: the two routes at the destination, the toll question, its buttons, its expiry, and the failures at the destination.
- `refuel-search`: the search uses the toll-free route when the user chose it.
- `routing-service`: the query service answers routes with `exclude=toll`.

## Impact

- Code: `gasolinera/osrm.py` (an `exclude` option on `Router`) and `gasolinera/bot.py` (the destination step, the toll question, and the router of the search). `gasolinera/refuel.py` does not change, because the search already takes the router as an argument.
- Tests: `gasolinera/tests/test_osrm.py` and `gasolinera/tests/test_bot_flow.py`. Two flow tests count route requests, and their counts change by 2.
- `README.md`: the toll question in the "Bot" section.
- No new setting, no new service, no rebuild of the graph, no new dependency.
