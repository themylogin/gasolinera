# Proposal

## Why

The store now holds every Spanish station with its prices and opening hours, but nobody can use it. A driver wants to send the bot a position and a destination and get the stations where they can refuel on the way, with the lowest cost of fuel and time first. A station must also be open when the driver arrives. The `french_tolls` bot and web page already do this for France, and this change brings the same flow to Spain, in Spanish.

## What Changes

- Add the command `/coche`. It asks the tank volume, the fuel type with three buttons (Gasolina 95, Gasolina 98, Diésel), the consumption at 80 km/h and at 120 km/h, and the value of the user's time in €/h. It stores one car for each Telegram user. A user with a car sees the values and chooses to change them.
- Add the journey flow:
  1. The user sends the origin.
  2. The bot asks for the destination.
  3. The bot asks how many liters are in the tank.
  4. The bot sends the 10 stops with the lowest cost, or says that no stop is needed.

  Each location is a Telegram location or `lat, lon` text.
- Add the command `/reiniciar`. It forgets the journey in progress and any open `/coche` dialog. It keeps the stored car.
- Add the command `/info`. It sends the usage help, the commands, and the tip links. `/start` and any message that the bot cannot use get the same text.
- Add the refuel search, as in `french_tolls`:
  1. Walk the route with the consumption curve until the tank holds 5 L.
  2. Take the 30 nearest stations within 50 km that sell the fuel group.
  3. Route a detour through each one.
  4. The stop fills the tank. Its cost is the liters × the price + the detour hours × the value of time.
  5. Sort by cost and keep 10.
- Add an opening-hours check. It parses `Horario`, takes the arrival time at each station in the station's time zone, and marks the station closed, or closing soon when it closes less than 20 minutes after arrival. A schedule that cannot be read, or that names only Monday, gives "Horario desconocido".
- Add a small OSRM client for `/nearest` and `/route` on the `osrm` service.
- Add the setting `TIME_MULTIPLIER` (default `0.933`). It corrects every OSRM duration, as in `french_tolls`.
- Add the `car` table.
- Every text the bot sends is in Spanish.

Out of scope:

- Place names as locations, and geocoding.
- Tolls.
- Public holidays in the schedule.
- More than one stop on a journey.
- Any cancel command other than `/reiniciar`.

## Capabilities

### New Capabilities

- `car-parameters`: the `/coche` dialog, its checks, and the stored car.
- `journey-dialog`: the order of messages from origin to answer, `/reiniciar`, `/info`, and the Spanish texts of the answer.
- `refuel-search`: the time correction, the route, the fuel walk, the candidates, the detours, the cost, the order, and the 10 stations of the answer.
- `opening-hours`: how `Horario` is read, and the open, closing soon, closed, and unknown state at an arrival time.

### Modified Capabilities

- `telegram-bot`: the bot now answers. It registers `/coche`, `/reiniciar`, `/info`, and `/start`, and it reaches `osrm` at `OSRM_URL`.
- `runtime-store`: the store now has a second application table, `car`.

## Impact

- New modules: `gasolinera/car.py`, `gasolinera/journey.py`, `gasolinera/refuel.py`, `gasolinera/opening_hours.py`, `gasolinera/osrm.py`. `gasolinera/bot.py` is rewritten.
- A new model and Alembic revision for `car`.
- Two new settings, `OSRM_URL` (default `http://osrm:5000`) and `TIME_MULTIPLIER` (default `0.933`), in `config.py` and `.env.example`.
- The bot now needs the `osrm` service and a filled store to answer a journey. It still starts without them.
- New tests, including a fake Telegram transport copied from `french_tolls/french_tolls/integration/telegram_transport.py`.
