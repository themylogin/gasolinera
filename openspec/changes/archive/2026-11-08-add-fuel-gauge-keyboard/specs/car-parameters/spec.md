# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: A user without a car gets five questions in a fixed order`
- TO: `### Requirement: A user without a car gets six questions in a fixed order`

## ADDED Requirements

### Requirement: The reserve is a number from 0 to 500 km

The reserve SHALL be a number from 0 to 500 km, with a point or a comma as the decimal separator. Any other answer SHALL make the bot send `La reserva debe ser un número de 0 a 500 km, por ejemplo 50. Escríbelo de nuevo.` and ask the same question again. A car stored before the reserve existed SHALL have a reserve of 50 km.

#### Scenario: A reserve

- **WHEN** the user answers the reserve with `60`
- **THEN** the bot saves the car with a reserve of 60 km

#### Scenario: A value that is too high

- **WHEN** the user answers the reserve with `600`
- **THEN** the bot sends the reserve error and keeps the same question

#### Scenario: A car from before the reserve

- **GIVEN** a car stored before the reserve existed
- **WHEN** the schema is applied
- **THEN** the car has a reserve of 50 km

## MODIFIED Requirements

### Requirement: The store keeps one car for each user

The store SHALL keep at most one car for each Telegram user id. A car SHALL hold the tank volume, the fuel group, the consumption at 80 km/h, the consumption at 120 km/h, the value of one hour of the user's time in €/h, and the reserve in km. Saving a car for a user who has one SHALL replace it.

#### Scenario: A second save replaces the first

- **GIVEN** user 777001 has a car with the fuel group `diesel`
- **WHEN** the user saves a car with the fuel group `gasoline_95`
- **THEN** the store has one car for user 777001, with the fuel group `gasoline_95`

### Requirement: A user without a car gets six questions in a fixed order

When a user without a car sends `/coche`, the bot SHALL ask, in this order:

1. `Escribe el volumen del depósito en litros.`;
2. `Elige el tipo de combustible.`, with buttons;
3. `Escribe el consumo a 80 km/h en litros por 100 km.`;
4. `Escribe el consumo a 120 km/h en litros por 100 km.`;
5. `¿Cuánto vale tu tiempo? Escríbelo en €/h, por ejemplo 20.`;
6. `¿Con cuántos kilómetros de autonomía quieres repostar? Escríbelo, por ejemplo 50.`

#### Scenario: The first question

- **WHEN** a user without a car sends `/coche`
- **THEN** the bot sends `Escribe el volumen del depósito en litros.`

#### Scenario: The second question

- **WHEN** the user answers the tank volume with `50`
- **THEN** the bot sends `Elige el tipo de combustible.` with the three fuel buttons

#### Scenario: The last question

- **WHEN** the user answers the value of time with `20`
- **THEN** the bot sends `¿Con cuántos kilómetros de autonomía quieres repostar? Escríbelo, por ejemplo 50.`

### Requirement: The value of time is a number from 0 to 1000

The value of time SHALL be a number from 0 to 1000 €/h, with a point or a comma as the decimal separator. Any other answer SHALL make the bot send `El valor de tu tiempo debe ser un número de 0 a 1000, por ejemplo 20. Escríbelo de nuevo.` and ask the same question again.

#### Scenario: Time that costs nothing

- **WHEN** the user answers the value of time with `0` and the reserve with `50`
- **THEN** the bot saves the car with 0 €/h

#### Scenario: A value that is too high

- **WHEN** the user answers the value of time with `1500`
- **THEN** the bot sends the value of time error and keeps the same question

### Requirement: The car is saved only after the last valid answer

The bot SHALL save the car only after a valid reserve. It SHALL then send `Tu coche está guardado.`, an empty line, and the car in the shown format. A dialog that stops before that SHALL change no stored car.

#### Scenario: The dialog stops after the fuel type

- **GIVEN** a user with a car with the fuel group `diesel`
- **WHEN** the user sends `/coche`, presses `Sí`, answers `50`, presses `Gasolina 98`, and then sends `/reiniciar`
- **THEN** the stored car still has the fuel group `diesel`

#### Scenario: The dialog stops before the reserve

- **GIVEN** a user with a car with a value of time of 20 €/h
- **WHEN** the user answers every question up to the value of time with `30`, and then sends `/reiniciar`
- **THEN** the stored car still has 20 €/h

### Requirement: The car is shown in one format

The bot SHALL show a car as six lines: `Depósito: <volume> L`, `Combustible: <label>`, `A 80 km/h: <value> L/100 km`, `A 120 km/h: <value> L/100 km`, `Tu tiempo: <value> €/h`, `Reserva: <value> km`. A value SHALL use a comma as the decimal separator and SHALL have no trailing zeros.

#### Scenario: A saved car

- **WHEN** a car has 50 L, `diesel`, 5.8, 7, 20 €/h, and 50 km
- **THEN** the bot shows `Depósito: 50 L`, `Combustible: Diésel`, `A 80 km/h: 5,8 L/100 km`, `A 120 km/h: 7 L/100 km`, `Tu tiempo: 20 €/h`, and `Reserva: 50 km`

### Requirement: A user with a car sees it and chooses to change it

When a user with a car sends `/coche`, the bot SHALL send `Tu coche:`, an empty line, the car in the shown format, an empty line, and `¿Quieres cambiarlo?`, with the buttons `Sí` and `No`. `Sí` SHALL start the six questions. `No` SHALL make the bot send `Tu coche no ha cambiado.` and end the dialog. Typed text while the question is open SHALL make the bot send `¿Quieres cambiarlo?` with the two buttons again.

#### Scenario: The user keeps the car

- **WHEN** a user with a car sends `/coche` and presses `No`
- **THEN** the bot sends `Tu coche no ha cambiado.`, and the stored car is unchanged

#### Scenario: The user changes the car

- **WHEN** a user with a car sends `/coche` and presses `Sí`
- **THEN** the bot sends `Escribe el volumen del depósito en litros.`
