# Spec Delta

## ADDED Requirements

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

## REMOVED Requirements

### Requirement: The bot does nothing

**Reason**: The bot now runs the car dialog and the journey flow.

**Migration**: None. No user relied on the silence.
