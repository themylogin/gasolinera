# car-parameters Specification

## Purpose

Lets each Telegram user enter and store the tank volume, the fuel group, the two consumptions of their car, and the value of their time, which the refuel search needs.

## Requirements

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

### Requirement: The tank volume is a whole number of 30 or more

The tank volume SHALL be a whole number of 30 or more, with no more than 18 digits. Any other answer SHALL make the bot send `El volumen del depósito debe ser un número entero de 30 o más. Escríbelo de nuevo.` and ask the same question again.

#### Scenario: A small value

- **WHEN** the user answers the tank volume with `25`
- **THEN** the bot sends the tank volume error and keeps the same question

#### Scenario: A decimal value

- **WHEN** the user answers the tank volume with `45,5`
- **THEN** the bot sends the tank volume error and keeps the same question

### Requirement: The fuel type is chosen with a button

The fuel question SHALL show one button for each fuel group, one button for each row, in this order: `Gasolina 95` for `gasoline_95`, `Gasolina 98` for `gasoline_98`, `Diésel` for `diesel`. After a press, the question SHALL become `Combustible: <label>` and SHALL have no buttons.

#### Scenario: The user presses Diésel

- **WHEN** the user presses `Diésel`
- **THEN** the question becomes `Combustible: Diésel`, and the bot asks the consumption at 80 km/h

#### Scenario: Text instead of a button

- **WHEN** the user types `diesel` while the fuel question is open
- **THEN** the bot sends `Elige el tipo de combustible con un botón.` with the three buttons again

### Requirement: A consumption is a number more than 0 and less than 30

A consumption SHALL be a number with a point or a comma as the decimal separator, more than 0 and less than 30. Any other answer SHALL make the bot send `El consumo debe ser un número mayor que 0 y menor que 30, por ejemplo 6,5. Escríbelo de nuevo.` and ask the same question again.

#### Scenario: A decimal comma

- **WHEN** the user answers the consumption at 80 km/h with `5,8`
- **THEN** the consumption at 80 km/h is 5.8

#### Scenario: A value that is too high

- **WHEN** the user answers `30`
- **THEN** the bot sends the consumption error and keeps the same question

#### Scenario: Text that is not a number

- **WHEN** the user answers `mucho`
- **THEN** the bot sends the consumption error and keeps the same question

### Requirement: The consumption at 120 km/h is not less than the consumption at 80 km/h

When the consumption at 120 km/h is less than the consumption at 80 km/h, the bot SHALL send `El consumo a 120 km/h debe ser igual o mayor que el consumo a 80 km/h, <value> L/100 km. Escríbelo de nuevo.` and ask again.

#### Scenario: A lower value at 120 km/h

- **GIVEN** the consumption at 80 km/h is 6
- **WHEN** the user answers the consumption at 120 km/h with `5`
- **THEN** the bot sends `El consumo a 120 km/h debe ser igual o mayor que el consumo a 80 km/h, 6 L/100 km. Escríbelo de nuevo.`

#### Scenario: An equal value

- **GIVEN** the consumption at 80 km/h is 6
- **WHEN** the user answers `6`
- **THEN** the bot asks `¿Cuánto vale tu tiempo? Escríbelo en €/h, por ejemplo 20.`

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

### Requirement: An open dialog takes the typed text of the user

While a `/coche` dialog is open, the bot SHALL read each typed text of that user as an answer to the open question. A Telegram location SHALL NOT be an answer. It SHALL go to the journey flow.

#### Scenario: Coordinates during the dialog

- **WHEN** the consumption question is open and the user types `40.42, -3.70`
- **THEN** the bot sends the consumption error

### Requirement: /coche during a dialog starts the dialog again

`/coche` SHALL end any open `/coche` dialog of that user and start a new one.

#### Scenario: /coche twice

- **WHEN** the user sends `/coche`, answers `50`, presses `Gasolina 95`, and sends `/coche` again
- **THEN** the bot asks the first question again

### Requirement: An old button changes nothing

A press on a button of a dialog that is not the open dialog of the user SHALL change no stored car and no open dialog. The bot SHALL remove the buttons of that message and send `Esta pregunta ha caducado. Envía /coche para empezar de nuevo.`

#### Scenario: A button from an earlier dialog

- **GIVEN** the user sent `/coche` and `50`, then `/coche` and `50` again
- **WHEN** the user presses `Gasolina 98` on the fuel question of the first dialog
- **THEN** the bot sends `Esta pregunta ha caducado. Envía /coche para empezar de nuevo.`, and the second dialog is still at its fuel question

### Requirement: A failed save is reported

When the store cannot save the car, the bot SHALL send `No he podido guardar tu coche. Lo siento mucho 😞` and end the dialog.

#### Scenario: The store fails

- **WHEN** the save raises an error
- **THEN** the bot sends `No he podido guardar tu coche. Lo siento mucho 😞`, and no dialog is open

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
