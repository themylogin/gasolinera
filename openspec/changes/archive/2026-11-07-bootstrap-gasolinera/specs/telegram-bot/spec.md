# Spec Delta

## Purpose

Runs the Telegram bot process of Gasolinera. For now the bot connects to Telegram and answers nothing.

## ADDED Requirements

### Requirement: The bot polls Telegram

The bot SHALL receive updates by long polling with the token in `TELEGRAM_BOT_TOKEN`. It SHALL publish no port.

#### Scenario: The bot starts with a token

- **WHEN** `TELEGRAM_BOT_TOKEN` holds a valid token and the `bot` service starts
- **THEN** the process polls Telegram for updates and keeps running

### Requirement: The bot does nothing

The bot SHALL register no update handler and no command. It SHALL send no message.

#### Scenario: A user sends a message

- **WHEN** a user sends `hello` to the bot
- **THEN** the bot sends no reply

#### Scenario: A user sends a command

- **WHEN** a user sends `/start` to the bot
- **THEN** the bot sends no reply

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
