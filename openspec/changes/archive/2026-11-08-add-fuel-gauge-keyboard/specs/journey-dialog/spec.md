# Spec Delta

## ADDED Requirements

### Requirement: The fuel question shows a gauge

The fuel question SHALL have an inline keyboard of four rows:

1. `1/1`, `.`, `.`, `.`, `3/4` for 16, 15, 14, 13, and 12 sixteenths;
2. `3/4`, `.`, `.`, `.`, `1/2` for 12, 11, 10, 9, and 8 sixteenths;
3. `1/2`, `.`, `.`, `.`, `1/4` for 8, 7, 6, 5, and 4 sixteenths;
4. `1/4`, `.`, `.`, `.` for 4, 3, 2, and 1 sixteenths.

#### Scenario: The keyboard

- **WHEN** the bot asks the fuel question
- **THEN** its rows are `1/1 . . . 3/4`, `3/4 . . . 1/2`, `1/2 . . . 1/4`, and `1/4 . . .`

#### Scenario: Two buttons with one value

- **WHEN** the user presses the `3/4` at the end of the first row, or the `3/4` at the start of the second row
- **THEN** the fuel is 12 sixteenths of the tank in both cases

### Requirement: A gauge press gives the fuel in the tank

A press SHALL start the refuel search with the tank volume multiplied by the sixteenths and divided by 16, in liters. The question SHALL become `Combustible: <mark> (<liters> L)` with no buttons. `<mark>` SHALL be the button label, or `<n>/16` for a `.` button. `<liters>` SHALL be rounded to one decimal, with a comma and no trailing zero.

#### Scenario: Half a tank

- **GIVEN** the tank volume is 50
- **WHEN** the user presses `1/2`
- **THEN** the question becomes `Combustible: 1/2 (25 L)`, and the search starts with 25 L

#### Scenario: A mark between two labels

- **GIVEN** the tank volume is 50
- **WHEN** the user presses the `.` for 13 sixteenths
- **THEN** the question becomes `Combustible: 13/16 (40,6 L)`, and the search starts with 40.625 L

### Requirement: A typed number is the range in kilometers

When the fuel question is open, the bot SHALL read typed text as a range in kilometers before it tries to read a location. The range SHALL be a number from 0 to 3000, with a point or a comma as the decimal separator. It SHALL start the refuel search with that range. Any other text SHALL make the bot send `Elige en el indicador o escribe los kilómetros de autonomía, por ejemplo 120.`

#### Scenario: A range

- **WHEN** the fuel question is open and the user types `120`
- **THEN** the search starts with a range of 120 km

#### Scenario: A decimal comma

- **WHEN** the fuel question is open and the user types `87,5`
- **THEN** the search starts with a range of 87.5 km

#### Scenario: Text that is not a range

- **WHEN** the fuel question is open and the user types `mucho`
- **THEN** the bot sends `Elige en el indicador o escribe los kilómetros de autonomía, por ejemplo 120.`, and the fuel question stays open

### Requirement: An old gauge button changes nothing

A press on a gauge that is not the gauge of the open fuel question of the user SHALL start no search and SHALL change no journey. The bot SHALL remove the buttons of that message and send `Esta pregunta ha caducado.`

#### Scenario: A gauge from an earlier journey

- **GIVEN** a user answered a fuel question, and then sent two new locations
- **WHEN** the user presses `1/2` on the first fuel question
- **THEN** the bot sends `Esta pregunta ha caducado.`, and the new fuel question is still open

#### Scenario: A gauge after /reiniciar

- **WHEN** the user sends `/reiniciar` and then presses a button of the fuel question
- **THEN** the bot sends `Esta pregunta ha caducado.`, and no search starts

## MODIFIED Requirements

### Requirement: The journey asks for the origin, the destination, and the fuel in order

The bot SHALL keep the journey of each user in memory. The first location SHALL be the origin, and the bot SHALL send `Ahora envíame el destino.` The second location SHALL be the destination, and the bot SHALL send `¿Cuánto combustible te queda? Elige en el indicador o escribe los kilómetros de autonomía.` with the gauge. A gauge press or a valid range SHALL start the refuel search.

#### Scenario: A complete journey

- **WHEN** a user with a car sends a location, a second location, and then presses `1/4`
- **THEN** the bot sends `Ahora envíame el destino.`, then the fuel question with the gauge, then the answer of the refuel search for a quarter of the tank

### Requirement: The answer when no stop is needed

When the fuel lasts to the destination, the bot SHALL send `No necesitas repostar: llegarás con <liters> L.`, where `<liters>` is the fuel left at the destination rounded down to a whole number. When the range lasts to the destination, the bot SHALL send `No necesitas repostar: llegarás con <km> km de autonomía.`, where `<km>` is the range left at the destination rounded down to a whole number.

#### Scenario: Enough fuel

- **WHEN** the search says 12.7 L are left at the destination
- **THEN** the bot sends `No necesitas repostar: llegarás con 12 L.`

#### Scenario: Enough range

- **WHEN** the search says 83.4 km of range are left at the destination
- **THEN** the bot sends `No necesitas repostar: llegarás con 83 km de autonomía.`

### Requirement: A failed search is reported

When the router does not answer or answers with an error, the bot SHALL send `No he podido calcular la ruta. Lo siento mucho 😞`, and then the fuel question again with a new gauge. When the router finds no route between the origin and the destination, the bot SHALL send `No encuentro una ruta por carretera entre el origen y el destino. Envíame tu ubicación actual.` and SHALL forget the journey.

#### Scenario: The router is down

- **WHEN** the user presses `1/2` and `osrm` does not answer
- **THEN** the bot sends `No he podido calcular la ruta. Lo siento mucho 😞` and the fuel question with a new gauge, and a press on that gauge starts the search again

## REMOVED Requirements

### Requirement: The liters are a number from 0 to the tank volume

**Reason**: A typed number is now the range in kilometers, and the gauge gives the fuel.

**Migration**: Press the gauge mark that is nearest to the fuel level, or type the range that the car shows.
