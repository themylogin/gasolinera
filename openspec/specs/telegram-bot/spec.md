# telegram-bot Specification

## Purpose

Runs the Telegram bot process of Gasolinera, which holds the `/coche` car dialog and the refuel journey, and reaches the routing service.

## Requirements

### Requirement: The bot polls Telegram

The bot SHALL receive updates by long polling with the token in `TELEGRAM_BOT_TOKEN`. It SHALL publish no port.

#### Scenario: The bot starts with a token

- **WHEN** `TELEGRAM_BOT_TOKEN` holds a valid token and the `bot` service starts
- **THEN** the process polls Telegram for updates and keeps running

### Requirement: The bot refuses to start without a token

The bot SHALL stop with a non-zero status and a message that names `TELEGRAM_BOT_TOKEN` when the variable is unset or empty. `make bot` SHALL make the same check before it starts a container.

#### Scenario: The process has no token

- **WHEN** the bot process starts with an empty `TELEGRAM_BOT_TOKEN`
- **THEN** it exits with a non-zero status and the message `gasolinera: cannot start: TELEGRAM_BOT_TOKEN is not set`

#### Scenario: make bot has no token

- **WHEN** `make bot` runs with an empty `TELEGRAM_BOT_TOKEN`
- **THEN** the target fails before it starts a container and names `TELEGRAM_BOT_TOKEN`

### Requirement: The bot starts after the schema is applied

The `bot` service SHALL start only after `migrate` completes with success. The bot SHALL NOT need the `osrm` service to start.

#### Scenario: No graph exists

- **WHEN** `OSRM_PATH` holds no graph and `make bot` runs with a valid token
- **THEN** the bot starts

### Requirement: The bot answers the journey and the car commands

The bot SHALL handle `/coche` as `car-parameters` defines it, `/reiniciar`, `/info`, and `/start` as `journey-dialog` defines them, and every location and text message as `journey-dialog` and `car-parameters` define them.

#### Scenario: A location reaches the journey flow

- **WHEN** a user with a car shares a location
- **THEN** the bot sends `Ahora envíame el destino.`

### Requirement: The command menu names the three commands in Spanish

At start, the bot SHALL set its command menu to `coche` with `Configurar tu coche`, then `reiniciar` with `Empezar de nuevo`, then `info` with `Qué hace este bot`. `/start` SHALL NOT be in the menu.

#### Scenario: The menu

- **WHEN** the bot starts
- **THEN** its command menu is `coche` "Configurar tu coche", `reiniciar` "Empezar de nuevo", and `info` "Qué hace este bot", in that order

### Requirement: The bot reaches the router at OSRM_URL

The bot SHALL send its routing requests to the address in `OSRM_URL`. When `OSRM_URL` is unset or empty, the address SHALL be `http://osrm:5000`.

#### Scenario: The default address

- **WHEN** `OSRM_URL` is not set
- **THEN** the bot sends its routing requests to `http://osrm:5000`
