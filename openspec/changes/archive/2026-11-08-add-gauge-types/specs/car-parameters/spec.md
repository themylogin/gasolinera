# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: A user without a car gets six questions in a fixed order`
- TO: `### Requirement: A user without a car gets seven questions in a fixed order`

## ADDED Requirements

### Requirement: The gauge is chosen on a picture

The gauge question SHALL be one photo: the three gauges side by side at one size, with no text on it. Its caption SHALL be `¿Cuántas secciones tiene tu indicador de combustible?` It SHALL have one row of three buttons, `24`, `16`, and `12`. After a press, the caption SHALL become `Indicador: <steps> secciones` and the photo SHALL have no buttons.

#### Scenario: The user presses 24

- **WHEN** the user presses `24`
- **THEN** the caption becomes `Indicador: 24 secciones`, and the bot asks `Elige el tipo de combustible.` with the three fuel buttons

#### Scenario: Text instead of a button

- **WHEN** the user types `24` while the gauge question is open
- **THEN** the bot sends the photo again with the caption `Elige tu indicador con un botón.` and the three buttons

### Requirement: A car stored before the gauge has 16 steps

A car stored before the gauge existed SHALL have a gauge of 16 steps.

#### Scenario: An old car

- **GIVEN** a car stored before the gauge existed
- **WHEN** the schema is applied
- **THEN** the car has a gauge of 16 steps

## MODIFIED Requirements

### Requirement: The store keeps one car for each user

The store SHALL keep at most one car for each Telegram user id. A car SHALL hold the tank volume, the gauge as its number of steps (24, 16, or 12), the fuel group, the consumption at 80 km/h, the consumption at 120 km/h, the value of one hour of the user's time in €/h, and the reserve in km. Saving a car for a user who has one SHALL replace it.

#### Scenario: A second save replaces the first

- **GIVEN** user 777001 has a car with the fuel group `diesel`
- **WHEN** the user saves a car with the fuel group `gasoline_95`
- **THEN** the store has one car for user 777001, with the fuel group `gasoline_95`

### Requirement: A user without a car gets seven questions in a fixed order

When a user without a car sends `/coche`, the bot SHALL ask, in this order:

1. `Escribe el volumen del depósito en litros.`;
2. the gauge question, as a photo with buttons;
3. `Elige el tipo de combustible.`, with buttons;
4. `Escribe el consumo a 80 km/h en litros por 100 km.`;
5. `Escribe el consumo a 120 km/h en litros por 100 km.`;
6. `¿Cuánto vale tu tiempo? Escríbelo en €/h, por ejemplo 20.`;
7. `¿Con cuántos kilómetros de autonomía quieres repostar? Escríbelo, por ejemplo 50.`

#### Scenario: The first question

- **WHEN** a user without a car sends `/coche`
- **THEN** the bot sends `Escribe el volumen del depósito en litros.`

#### Scenario: The second question

- **WHEN** the user answers the tank volume with `50`
- **THEN** the bot sends the gauge photo with the buttons `24`, `16`, and `12`

#### Scenario: The last question

- **WHEN** the user answers the value of time with `20`
- **THEN** the bot sends `¿Con cuántos kilómetros de autonomía quieres repostar? Escríbelo, por ejemplo 50.`

### Requirement: The car is shown in one format

The bot SHALL show a car as seven lines: `Depósito: <volume> L`, `Indicador: <steps> secciones`, `Combustible: <label>`, `A 80 km/h: <value> L/100 km`, `A 120 km/h: <value> L/100 km`, `Tu tiempo: <value> €/h`, `Reserva: <value> km`. A value SHALL use a comma as the decimal separator and SHALL have no trailing zeros.

#### Scenario: A saved car

- **WHEN** a car has 50 L, a gauge of 16 steps, `diesel`, 5.8, 7, 20 €/h, and 50 km
- **THEN** the bot shows `Depósito: 50 L`, `Indicador: 16 secciones`, `Combustible: Diésel`, `A 80 km/h: 5,8 L/100 km`, `A 120 km/h: 7 L/100 km`, `Tu tiempo: 20 €/h`, and `Reserva: 50 km`

### Requirement: A user with a car sees it and chooses to change it

When a user with a car sends `/coche`, the bot SHALL send `Tu coche:`, an empty line, the car in the shown format, an empty line, and `¿Quieres cambiarlo?`, with the buttons `Sí` and `No`. `Sí` SHALL start the seven questions. `No` SHALL make the bot send `Tu coche no ha cambiado.` and end the dialog. Typed text while the question is open SHALL make the bot send `¿Quieres cambiarlo?` with the two buttons again.

#### Scenario: The user keeps the car

- **WHEN** a user with a car sends `/coche` and presses `No`
- **THEN** the bot sends `Tu coche no ha cambiado.`, and the stored car is unchanged

#### Scenario: The user changes the car

- **WHEN** a user with a car sends `/coche` and presses `Sí`
- **THEN** the bot sends `Escribe el volumen del depósito en litros.`

### Requirement: The car is saved only after the last valid answer

The bot SHALL save the car only after a valid reserve. It SHALL then send `Tu coche está guardado.`, an empty line, and the car in the shown format. A dialog that stops before that SHALL change no stored car.

#### Scenario: The dialog stops after the fuel type

- **GIVEN** a user with a car with the fuel group `diesel`
- **WHEN** the user sends `/coche`, presses `Sí`, answers `50`, presses `16`, presses `Gasolina 98`, and then sends `/reiniciar`
- **THEN** the stored car still has the fuel group `diesel`

#### Scenario: The dialog stops before the reserve

- **GIVEN** a user with a car with a value of time of 20 €/h
- **WHEN** the user answers every question up to the value of time with `30`, and then sends `/reiniciar`
- **THEN** the stored car still has 20 €/h

### Requirement: /coche during a dialog starts the dialog again

`/coche` SHALL end any open `/coche` dialog of that user and start a new one.

#### Scenario: /coche twice

- **WHEN** the user sends `/coche`, answers `50`, presses `24`, presses `Gasolina 95`, and sends `/coche` again
- **THEN** the bot asks the first question again

### Requirement: An old button changes nothing

A press on a button of a dialog that is not the open dialog of the user SHALL change no stored car and no open dialog. The bot SHALL remove the buttons of that message and send `Esta pregunta ha caducado. Envía /coche para empezar de nuevo.`

#### Scenario: A button from an earlier dialog

- **GIVEN** the user sent `/coche` and `50`, then `/coche` and `50` again
- **WHEN** the user presses `12` on the gauge question of the first dialog
- **THEN** the bot sends `Esta pregunta ha caducado. Envía /coche para empezar de nuevo.`, and the second dialog is still at its gauge question
