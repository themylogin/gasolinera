# Gasolinera

A Telegram bot that finds where to refuel on a route across Spain, at the
lowest cost of fuel and time.

## Prerequisites

* Linux with Docker, the Compose plugin, and GNU make.
* 12 GB RAM. `osrm-extract` peaks at about 11 GB.
* 10 GB free disk at `OSRM_PATH`. The Makefile refuses to start the
  preprocessing with less.

Every step runs in a container. If your user cannot reach the Docker socket,
add `DOCKER="sudo -n docker"` to each `make` command.

## Configuration

```
cp .env.example .env
```

| Variable | Purpose |
| --- | --- |
| `OSRM_PATH` | absolute path of the routing graph |
| `TELEGRAM_BOT_TOKEN` | the token that BotFather issued |
| `OSRM_URL` | the routing service; empty means the `osrm` service |
| `TIME_MULTIPLIER` | OSRM's travel times are multiplied by this; default 0.933 |
| `LOG_LEVEL` | the log level of the bot |

## Build the routing graph

```
make all
```

`make all` downloads https://download.geofabrik.de/europe/spain-latest.osm.pbf
to `data/` and builds the graph at `OSRM_PATH` with the default car profile of
OSRM. Each step is skipped when its output is already in place. A newer extract
does not start a rebuild. To rebuild, run `make clean-osrm` and then `make all`.

## Run

```
make osrm   # the routing service, on http://osrm:5000 inside the Compose network
make bot    # the Telegram bot
make down   # stop everything
```

`make bot` applies the database schema first. The database is
`/cache/database.db` on the Compose volume `cache`.

## Bot

The bot needs the routing service and the gas stations. Start them first:

```
make osrm
make gas-stations
make bot
```

In Telegram:

1. `/coche` asks the tank volume, the gauge that looks like yours, the fuel
   type, the consumption at 80 km/h and at 120 km/h, what an hour of your time
   is worth, and the reserve: how many kilometers of range you want left when
   you refuel.
2. Send your location, then the destination. A location is a shared
   location or `lat, lon` text.
3. Press the mark of your gauge nearest to the needle, or type the range in
   kilometers that your car shows.

With the gauge, the bot plans the stop where the tank holds 5 L. `0` plans it
at your location. With a typed
range, it plans the stop where the range drops to your reserve.

The bot lists the 10 stops with the lowest cost: the fuel for a full tank,
plus the detour time at your hourly value. It warns when a station will be
closed, or will close less than 20 minutes after you arrive.

`/reiniciar` forgets the journey and keeps the car. `/info` shows the help.

The Geofabrik extract of Spain does not contain the Canary Islands: Geofabrik
lists them separately. The bot therefore refuses a location there, and it
cannot route to the Canary stations in the store.

OSRM's travel times are multiplied by `TIME_MULTIPLIER`. The default 0.933
comes from `french_tolls`, which measured it against Google on French roads.

## The gauge picture

`/coche` shows `gasolinera/assets/gauges.png`: the three gauges of `gauge/` at
one size, labeled with the steps of their keyboards. After a change in
`gauge/`, render it again and commit it:

```
make gauge-image
```

## Gas stations

```
make gas-stations
```

The run downloads every station of
https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/
in one request. It replaces the stored stations with that list. The source
updates its prices every half hour.

## Tests

```
make test
```

The suite needs no `.env` and no graph.

## Dependencies

Declare dependencies in `pyproject.toml`. Then run:

```
make requirements
```

Commit both `pyproject.toml` and `requirements.txt`.
