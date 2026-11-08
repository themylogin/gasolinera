# Spec Delta

## ADDED Requirements

### Requirement: The destination question offers the nearby stations

Each `Ahora envíame el destino.` message SHALL have one inline button: `o mostrar gasolineras cercanas`.

#### Scenario: After the origin

- **WHEN** a user with a car sends a location
- **THEN** the bot sends `Ahora envíame el destino.` with the one button `o mostrar gasolineras cercanas`

### Requirement: A press on the nearby button lists the stations and ends the journey

A press on `o mostrar gasolineras cercanas` SHALL send the list of `nearby-stations` for the origin and the fuel group of the car. The bot SHALL remove the button and keep the text `Ahora envíame el destino.` The press SHALL forget the journey, so the next location is a new origin.

#### Scenario: The list

- **GIVEN** a station that sells the fuel of the car is 0.4 km from the origin
- **WHEN** the user sends a location and presses `o mostrar gasolineras cercanas`
- **THEN** the bot sends the list, and the first line of the list ends with `· 0,4 km`

#### Scenario: After the list

- **WHEN** the user presses `o mostrar gasolineras cercanas` and then sends a location
- **THEN** the bot sends `Ahora envíame el destino.`

### Requirement: An old nearby button changes nothing

A press on a nearby button that is not on the open destination question of the user SHALL send no list and SHALL change no journey. The bot SHALL remove the buttons of that message and send `Esta pregunta ha caducado.`

#### Scenario: After the destination

- **WHEN** the user sends a location, a second location, and then presses `o mostrar gasolineras cercanas`
- **THEN** the bot sends `Esta pregunta ha caducado.`, and the fuel question is still open

#### Scenario: After a new origin

- **GIVEN** the user sent an origin and a destination, and then a location during the fuel question as a new origin
- **WHEN** the user presses the button of the first `Ahora envíame el destino.`
- **THEN** the bot sends `Esta pregunta ha caducado.`, and the button of the second message still sends the list

#### Scenario: After /reiniciar

- **WHEN** the user sends a location, then `/reiniciar`, and then presses `o mostrar gasolineras cercanas`
- **THEN** the bot sends `Esta pregunta ha caducado.`, and no list is sent

#### Scenario: A second press

- **WHEN** the user presses `o mostrar gasolineras cercanas` twice on the same message
- **THEN** the bot sends one list and then `Esta pregunta ha caducado.`
