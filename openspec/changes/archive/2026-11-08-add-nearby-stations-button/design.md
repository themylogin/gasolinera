# Design

## Context

- `bot.handle_location` keeps `Journey(origin=…)` and sends `Ahora envíame el destino.` from one place, with no keyboard. It keeps an origin only for a user with a car, so the fuel type is known when the button is pressed.
- `refuel.candidates(position, fuel_type)` already gives the stations within 50 km that sell the fuel group. It sorts them by great-circle distance and then by id, and keeps 30. Each `Candidate` holds the station, the price, and `distance_km`.
- `journey.format_answer` writes the refuel answer. Its private helpers write the link, the escaped name, the price, and the alert line from a `Listed`.
- The gauge and the toll buttons use a token in the `Journey` and in the callback data. A press with another token gets `Esta pregunta ha caducado.`

## Goals / Non-Goals

**Goals:**

- Reuse `candidates` for the filter, the radius, and the order.
- Reuse the link, name, price, and alert code of the refuel answer, so the two lists look alike.

**Non-Goals:**

- A route request. The list is instant and works when `osrm` is down.

## Decisions

### The nearby list is built on candidates

`refuel.nearby(position, fuel_type, now)` returns a tuple of `Nearby(station, price, distance_km, local_time, state)`:

1. `found = (await candidates(position, fuel_type))[:10]`.
2. For each candidate, `local_time = now.astimezone(station_zone(station.province))`, and `state = state_at(station.opening_hours, local_time)`.

- `candidates` already does the 50 km filter, the fuel group, and the tie on the id. The nearby spec states the same rules, so the code does not repeat them.
- `local_time` is kept, because the alert of a closed station shows the time.
- Alternative: build `Listed` with `detour_s=0` and reuse `format_answer`. The second line then shows `+0 min`, and the first line shows whole km. Rejected.

### The format reuses the station helpers

`journey.format_nearby(stations, fuel_label)`:

- empty: `Ninguna gasolinera vende {fuel_label} a menos de 50 km de tu ubicación.`;
- otherwise, the station blocks joined by an empty line.

The link, the escaped name, the price text, and the alert text move into small helpers that take plain values. `_station_lines` and the new nearby lines both call them. The alert helper takes the state and the time to show for `closed`. For the refuel answer that time is the arrival. For the nearby list it is `local_time`.

The distance is `f"{distance_km:.1f}"` with a comma.

### The button carries a token

- `Journey` gets `nearby_token: str | None = None`. `ChatState.new_nearby_token()` gives `n<n>` from the shared counter.
- The origin step stores `Journey(origin=location, nearby_token=token)`, and sends the text with one button, callback data `nearby:<token>`.
- The destination step builds a new `Journey(origin=…, destination=…)`, so the token is gone. `/reiniciar` forgets the journey. A new origin gets a new token. So every old button expires with no extra code.

### The press

`nearby_button_handler` on `^nearby:`:

1. The journey must exist, have no destination, and have the same `nearby_token`. The car must exist. Otherwise, remove the buttons and send `Esta pregunta ha caducado.`
2. Forget the journey before the first `await`, so a second press expires.
3. Remove the button with `edit_message_reply_markup(reply_markup=None)`. The text stays.
4. Call `refuel.nearby(journey.origin, parameters.fuel_type, now)`, and send `format_nearby` as HTML with no link preview.

When `nearby` raises, the handler logs a warning and sends `No he podido buscar las gasolineras. Lo siento mucho 😞`. The journey is already forgotten, so the user starts again with a location.

### Tests

- `test_refuel.py`: `nearby` keeps 10 of 12 stations, in distance order, and gives the state at `now` in the time zone of the station.
- `test_journey.py`: the two lines, the `0,4 km` and `12,5 km` texts, the three alerts, and the empty text.
- `test_bot_flow.py`: the button on `Ahora envíame el destino.`, the press, the next location, and the four expiry cases. No existing test asserts the markup of that message, so the existing tests need no change.

## Risks / Trade-offs

- [A straight-line distance hides a river or a motorway between the user and the station] → The user asked for a simple sort. The Google Maps link shows the real way.
- [A station listed as open closes before the user arrives] → The state is for now, not for an arrival. `Cierra pronto` warns when less than 20 minutes are left.
- [The refactor of the station helpers changes the refuel answer] → The existing `test_journey.py` tests of the refuel answer must pass with no change.

## Migration Plan

Deploy the code and run `make bot`. Rollback: revert the code and run `make bot`.
