# journey-dialog Specification

## Purpose

Defines the Spanish conversation that takes a user from their position and destination to the list of stations where they can refuel, and how `/reiniciar` resets it.

## Requirements

### Requirement: A location is a Telegram location or typed coordinates

The bot SHALL read a location from a Telegram location message, or from typed text that holds `<latitude>, <longitude>` as two decimal numbers with a point. A minus sign SHALL be allowed on both numbers.

#### Scenario: Typed coordinates west of Greenwich

- **WHEN** the user types `40.4168, -3.7038`
- **THEN** the location is latitude 40.4168 and longitude -3.7038

#### Scenario: A shared location

- **WHEN** the user shares a Telegram location
- **THEN** the location is the latitude and longitude of that message

### Requirement: The journey asks for the origin, the destination, and the fuel in order

The bot SHALL keep the journey of each user in memory. The first location SHALL be the origin, and the bot SHALL send `Ahora envíame el destino.` The second location SHALL be the destination. The bot SHALL then route the journey with and without tolls, and SHALL send the toll question when the two routes differ. After that, the bot SHALL send `¿Cuánto combustible te queda? Elige en el indicador o escribe los kilómetros de autonomía.` with the gauge. A gauge press or a valid range SHALL start the refuel search.

#### Scenario: A complete journey

- **GIVEN** the routes with and without tolls are the same
- **WHEN** a user with a car sends a location, a second location, and then presses `1/4`
- **THEN** the bot sends `Ahora envíame el destino.`, then the fuel question with the gauge, then the answer of the refuel search for a quarter of the tank

#### Scenario: A complete journey with the toll question

- **GIVEN** the routes with and without tolls differ
- **WHEN** a user with a car sends a location, a second location, presses `No`, and then presses `1/4`
- **THEN** the bot sends `Ahora envíame el destino.`, then the toll question, then the fuel question with the gauge, then the answer of the refuel search for a quarter of the tank

### Requirement: The journey needs a car

When a user without a car sends an origin, the bot SHALL send `Primero dime cómo es tu coche con /coche.` and SHALL NOT keep the origin.

#### Scenario: No car

- **WHEN** a user without a car sends a location
- **THEN** the bot sends `Primero dime cómo es tu coche con /coche.`, and the next location is an origin again

### Requirement: A location far from the road network is refused

The bot SHALL refuse a location that is more than 1,000 m from the nearest road of the graph. It SHALL send `🇪🇸 Esta ubicación no está a menos de 1 km de ninguna carretera de España.` and SHALL keep the journey as it was.

#### Scenario: A position at sea

- **GIVEN** a user whose origin is kept
- **WHEN** the user sends a location 5 km from any road
- **THEN** the bot sends the refusal, and the next location is still the destination

### Requirement: A location during the fuel question starts a new journey

When the fuel question is open, a Telegram location SHALL become the origin of a new journey, and the bot SHALL send `Ahora envíame el destino.`

#### Scenario: A new origin

- **WHEN** the fuel question is open and the user shares a location
- **THEN** the bot sends `Ahora envíame el destino.`, and the next location is the destination

### Requirement: The answer ends the journey

After the bot sends the answer of a search, the next location SHALL be a new origin.

#### Scenario: After the answer

- **WHEN** the bot has sent the list of stations and the user sends a location
- **THEN** the bot sends `Ahora envíame el destino.`

### Requirement: /reiniciar resets the conversation but not the car

`/reiniciar` SHALL forget the journey and any open `/coche` dialog of the user. It SHALL NOT change the stored car. The bot SHALL send `Envíame tu ubicación actual.`

#### Scenario: Reset after the origin

- **GIVEN** a user whose origin is kept
- **WHEN** the user sends `/reiniciar` and then a location
- **THEN** that location is the origin, and the stored car is unchanged

### Requirement: /info, /start, and other text get the info text

The bot SHALL send the info text on `/info`, on `/start`, and when it cannot use a message, without a link preview. `/info` SHALL NOT change the journey or an open `/coche` dialog.

#### Scenario: A greeting

- **WHEN** a user with no open question types `hola`
- **THEN** the bot sends the info text, and Telegram shows no preview of its links

#### Scenario: /info during a journey

- **GIVEN** a user whose origin is kept
- **WHEN** the user sends `/info` and then a location
- **THEN** the bot sends the info text, and that location is the destination

### Requirement: The info text explains the use

The info text SHALL start with these lines:

```
Este bot busca dónde repostar más barato en tu ruta por España.

1. Configura tu coche con /coche.
2. Envíame tu ubicación actual.
3. Envíame el destino.
4. Dime cuántos litros te quedan.

Te mostraré las 10 paradas más baratas, contando el combustible y el tiempo del desvío, y te avisaré si una gasolinera estará cerrada o a punto de cerrar cuando llegues.
```

#### Scenario: The steps

- **WHEN** the bot sends the info text
- **THEN** its second paragraph lists the four steps, numbered from 1 to 4

### Requirement: The info text lists the commands and the tip links

After the use, the info text SHALL have an empty line and these lines:

```
/coche: configurar tu coche
/reiniciar: empezar de nuevo
/info: esta información

Puedes decirme gracias aquí: https://buymeacoffee.com/themylogin o https://paypal.me/themyloginspain
```

#### Scenario: The tip links

- **WHEN** the bot sends the info text
- **THEN** its last line holds `https://buymeacoffee.com/themylogin` and `https://paypal.me/themyloginspain`

### Requirement: The answer when no stop is needed

When the fuel lasts to the destination, the bot SHALL send `No necesitas repostar: llegarás con <liters> L.`, where `<liters>` is the fuel left at the destination rounded down to a whole number. When the range lasts to the destination, the bot SHALL send `No necesitas repostar: llegarás con <km> km de autonomía.`, where `<km>` is the range left at the destination rounded down to a whole number.

#### Scenario: Enough fuel

- **WHEN** the search says 12.7 L are left at the destination
- **THEN** the bot sends `No necesitas repostar: llegarás con 12 L.`

#### Scenario: Enough range

- **WHEN** the search says 83.4 km of range are left at the destination
- **THEN** the bot sends `No necesitas repostar: llegarás con 83 km de autonomía.`

### Requirement: The answer when no station is near

When the search finds no station, the bot SHALL send `Ninguna gasolinera vende <label> a menos de 50 km del punto donde el depósito llega a 5 L.`, where `<label>` is the label of the fuel group of the car.

#### Scenario: No diesel near

- **WHEN** the car uses `diesel` and the search finds no station
- **THEN** the bot sends `Ninguna gasolinera vende Diésel a menos de 50 km del punto donde el depósito llega a 5 L.`

### Requirement: The answer lists the stations in one message

The bot SHALL send the stations in one HTML message without a link preview and without a header. The stations SHALL be numbered from 1, in the order of the search, with an empty line between two stations.

#### Scenario: The first line

- **WHEN** the search lists 10 stations
- **THEN** the bot sends one message whose first line is the first line of station 1, and the stations are numbered from 1 to 10

### Requirement: Each listed station has two lines and an alert when needed

Each station SHALL have two lines:

1. its number and its name as a link to its Google Maps position, then ` · ` and the road distance from the origin in whole km;
2. the price with three decimals and a comma followed by ` €/L`, then ` · ` and the detour in whole minutes with a sign.

An alert line SHALL follow only when the opening state is not `open`.

#### Scenario: One open station

- **WHEN** the first station is `GALP`, with 1.499, 410.3 km from the origin, and a detour of 100 s
- **THEN** its lines are `1. <a href="https://www.google.com/maps/search/?api=1&amp;query=…">GALP</a> · 410 km` and `1,499 €/L · +2 min`, and it has no alert line

#### Scenario: A shorter route through the station

- **WHEN** the detour of a station is -70 s
- **THEN** its second line ends with `· -1 min`

### Requirement: The station texts are safe HTML

The bot SHALL escape the name of a station for HTML. An empty name SHALL be shown as `Gasolinera sin nombre`.

#### Scenario: A name with HTML characters

- **WHEN** the station name is `A&B <24h>`
- **THEN** the message shows `A&amp;B &lt;24h&gt;`

#### Scenario: No name

- **WHEN** the station name is empty
- **THEN** the message shows `Gasolinera sin nombre` as the link text

### Requirement: The alert line names the opening state in Spanish

The alert line SHALL be:

- for closed: `⚠️ <b>Cerrada</b> a las <arrival>`;
- for closing soon: `⚠️ <b>Cierra pronto</b> a las <closing>`;
- for unknown: `⚠️ <b>Horario desconocido</b>`.

The times SHALL be `HH:MM` in the time zone of the station.

#### Scenario: Closed at the arrival

- **WHEN** a station is closed when the user arrives at 22:41
- **THEN** its alert line is `⚠️ <b>Cerrada</b> a las 22:41`

#### Scenario: Closing soon

- **WHEN** a station is reached at 21:45 and closes at 22:00
- **THEN** its alert line is `⚠️ <b>Cierra pronto</b> a las 22:00`

#### Scenario: A Monday-only schedule

- **WHEN** the schedule of a station is `L: 24H`
- **THEN** its alert line is `⚠️ <b>Horario desconocido</b>`

### Requirement: A failed search is reported

When the router does not answer or answers with an error, the bot SHALL send `No he podido calcular la ruta. Lo siento mucho 😞`, and then the fuel question again with a new gauge. When the router finds no route between the origin and the destination, the bot SHALL send `No encuentro una ruta por carretera entre el origen y el destino. Envíame tu ubicación actual.` and SHALL forget the journey.

#### Scenario: The router is down

- **WHEN** the user presses `1/2` and `osrm` does not answer
- **THEN** the bot sends `No he podido calcular la ruta. Lo siento mucho 😞` and the fuel question with a new gauge, and a press on that gauge starts the search again

### Requirement: The fuel question shows a gauge

The fuel question SHALL have the inline keyboard of the gauge of the car: the 24-step, the 16-step, or the 12-step gauge. A row SHALL repeat the label that ends the row before it, and both buttons SHALL have the same value.

#### Scenario: The keyboard

- **GIVEN** a car with a gauge of 12 steps
- **WHEN** the bot asks the fuel question
- **THEN** the keyboard is the 12-step gauge

#### Scenario: Two buttons with one value

- **GIVEN** a car with a gauge of 16 steps
- **WHEN** the user presses the `3/4` at the end of the first row, or the `3/4` at the start of the second row
- **THEN** the fuel is three quarters of the tank in both cases

### Requirement: A gauge press gives the fuel in the tank

A press SHALL start the refuel search with the tank volume multiplied by the step of the button and divided by the steps of the gauge, in liters. The question SHALL become `Combustible: <mark> (<liters> L)` with no buttons. `<mark>` SHALL be the button label, or the reduced fraction of the step for a `.`, `,`, or `|` button. `<liters>` SHALL be rounded to one decimal, with a comma and no trailing zero.

#### Scenario: Half a tank

- **GIVEN** a car with a tank of 50 L and a gauge of 16 steps
- **WHEN** the user presses `1/2`
- **THEN** the question becomes `Combustible: 1/2 (25 L)`, and the search starts with 25 L

#### Scenario: A mark between two labels

- **GIVEN** a car with a tank of 50 L and a gauge of 24 steps
- **WHEN** the user presses the `|` for step 21
- **THEN** the question becomes `Combustible: 7/8 (43,8 L)`, and the search starts with 43.75 L

#### Scenario: A full tank

- **GIVEN** a car with a tank of 50 L and a gauge of 12 steps
- **WHEN** the user presses `1`
- **THEN** the question becomes `Combustible: 1 (50 L)`

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

### Requirement: The 24-step gauge

The 24-step gauge SHALL have four rows. Each row SHALL be one quarter of the tank, from its top to its bottom, one button for each step:

1. `1`, `.`, `.`, `|`, `.`, `.`, `3/4` for 24 down to 18;
2. `3/4`, `.`, `.`, `|`, `.`, `.`, `1/2` for 18 down to 12;
3. `1/2`, `.`, `.`, `|`, `.`, `.`, `1/4` for 12 down to 6;
4. `1/4`, `.`, `.`, `|`, `.`, `.`, `0` for 6 down to 0.

#### Scenario: The rows

- **WHEN** the car has a gauge of 24 steps and the bot asks the fuel question
- **THEN** the rows are `1 . . | . . 3/4`, `3/4 . . | . . 1/2`, `1/2 . . | . . 1/4`, and `1/4 . . | . . 0`

### Requirement: The 16-step gauge

The 16-step gauge SHALL have four rows. Each row SHALL be one quarter of the tank, from its top to its bottom, one button for each step:

1. `1`, `.`, `|`, `,`, `3/4` for 16 down to 12;
2. `3/4`, `.`, `|`, `,`, `1/2` for 12 down to 8;
3. `1/2`, `.`, `|`, `,`, `1/4` for 8 down to 4;
4. `1/4`, `.`, `|`, `,`, `0` for 4 down to 0.

#### Scenario: The rows

- **WHEN** the car has a gauge of 16 steps and the bot asks the fuel question
- **THEN** the rows are `1 . | , 3/4`, `3/4 . | , 1/2`, `1/2 . | , 1/4`, and `1/4 . | , 0`

### Requirement: The 12-step gauge

The 12-step gauge SHALL have two rows. Each row SHALL be one half of the tank, from its top to its bottom, one button for each step:

1. `1`, `.`, `5/6`, `.`, `2/3`, `.`, `1/2` for 12 down to 6;
2. `1/2`, `.`, `1/3`, `.`, `1/6`, `.`, `0` for 6 down to 0.

#### Scenario: The rows

- **WHEN** the car has a gauge of 12 steps and the bot asks the fuel question
- **THEN** the rows are `1 . 5/6 . 2/3 . 1/2` and `1/2 . 1/3 . 1/6 . 0`

### Requirement: The 0 mark plans the stop at the origin

A press on `0` SHALL start the refuel search with 0 L. The search point is then the origin, because the tank holds 5 L or less there.

#### Scenario: An empty tank

- **GIVEN** a car with a tank of 50 L
- **WHEN** the user presses `0`
- **THEN** the question becomes `Combustible: 0 (0 L)`, and the search looks for stations near the origin

### Requirement: The destination is routed with and without tolls

When the bot accepts a destination, it SHALL request the route from the origin to the destination twice from `osrm`: once as it is, and once with toll roads excluded. Two routes SHALL be the same when they pass through the same points in the same order. When they are the same, the bot SHALL send the fuel question with no toll question, and the search SHALL use the route with tolls allowed.

#### Scenario: Barcelona to Lleida

- **WHEN** the user sends Barcelona `41.3851, 2.1734` as the origin and Lleida `41.6176, 0.6200` as the destination
- **THEN** both routes pass through the same points, and the bot sends the fuel question and no toll question

#### Scenario: Same routes in the search

- **GIVEN** both routes pass through the same points
- **WHEN** the user presses `1/2`
- **THEN** no route request of the search excludes tolls

### Requirement: The toll question shows the time that the tolls save

When the two routes differ, the bot SHALL send `¿Quieres usar autopistas de peaje?` with one row of two buttons: `Sí (-<minutes> min)` and `No`. `<minutes>` SHALL be the duration of the toll-free route minus the duration of the route with tolls, multiplied by `TIME_MULTIPLIER`, and rounded to whole minutes.

#### Scenario: Barcelona to Puigcerdà

- **WHEN** the user sends Barcelona `41.3851, 2.1734` as the origin and Puigcerdà `42.4317, 1.9280` as the destination
- **THEN** the bot sends `¿Quieres usar autopistas de peaje?` with the buttons `Sí (-<minutes> min)` and `No`, and `<minutes>` is more than 0

#### Scenario: Tolls save 44 minutes

- **GIVEN** `TIME_MULTIPLIER` is `0.933`
- **WHEN** the routes differ, the route with tolls takes 7,400 s, and the toll-free route takes 10,201 s
- **THEN** the bot sends `¿Quieres usar autopistas de peaje?` with the buttons `Sí (-44 min)` and `No`

#### Scenario: More than one hour

- **GIVEN** `TIME_MULTIPLIER` is `0.933`
- **WHEN** the routes differ, the route with tolls takes 7,400 s, and the toll-free route takes 12,224 s
- **THEN** the buttons are `Sí (-75 min)` and `No`

### Requirement: No toll question when the tolls save no time

When the two routes differ and `<minutes>` is 0 or less, the bot SHALL send no toll question. It SHALL send the fuel question, and the search SHALL use the toll-free route.

#### Scenario: The toll-free route is as fast

- **GIVEN** `TIME_MULTIPLIER` is `0.933`
- **WHEN** the routes differ, the route with tolls takes 7,400 s, and the toll-free route takes 7,420 s
- **THEN** the bot sends the fuel question and no toll question, and every route request of the search excludes tolls

### Requirement: A toll press chooses the route of the search

A press on `Sí` SHALL make the search use the route with tolls allowed. A press on `No` SHALL make the search use the toll-free route. The toll question SHALL become `Peajes: ` and the label of the pressed button, with no buttons. The bot SHALL then send the fuel question with the gauge.

#### Scenario: With tolls

- **WHEN** the user presses `Sí (-44 min)` and then `1/2`
- **THEN** the toll question becomes `Peajes: Sí (-44 min)`, the bot sends the fuel question, and no route request of the search excludes tolls

#### Scenario: Without tolls

- **WHEN** the user presses `No` and then `1/2`
- **THEN** the toll question becomes `Peajes: No`, and the planned route and every detour of the search exclude tolls

#### Scenario: The choice survives a failed search

- **GIVEN** the user pressed `No`
- **WHEN** the search fails because `osrm` does not answer, and the user presses `1/2` on the new gauge
- **THEN** every route request of the second search excludes tolls

### Requirement: The route with tolls is used when the toll-free request fails

When the toll-free request finds no route, gets no answer, or gets an error, the bot SHALL send no toll question. It SHALL send the fuel question, and the search SHALL use the route with tolls allowed.

#### Scenario: The toll-free request gets no answer

- **WHEN** the user sends a destination and the toll-free request gets no answer
- **THEN** the bot sends the fuel question with the gauge, and no route request of the search excludes tolls

#### Scenario: No route without tolls

- **WHEN** the toll-free request answers `NoRoute`
- **THEN** the bot sends the fuel question and no toll question

### Requirement: A failed route at the destination is reported

When the request with tolls allowed gets no answer or gets an error, the bot SHALL send `No he podido calcular la ruta. Lo siento mucho 😞` and SHALL keep the origin. When it finds no route, the bot SHALL send `No encuentro una ruta por carretera entre el origen y el destino. Envíame tu ubicación actual.` and SHALL forget the journey.

#### Scenario: The router is down at the destination

- **WHEN** the user sends a destination and `osrm` does not answer the route request
- **THEN** the bot sends `No he podido calcular la ruta. Lo siento mucho 😞`, and the next location is the destination again

#### Scenario: No road between the points

- **WHEN** the user sends a destination and `osrm` answers `NoRoute`
- **THEN** the bot sends `No encuentro una ruta por carretera entre el origen y el destino. Envíame tu ubicación actual.`, and the next location is an origin

### Requirement: A location during the toll question starts a new journey

When the toll question is open, a Telegram location or typed coordinates SHALL become the origin of a new journey, and the bot SHALL send `Ahora envíame el destino.` Other text SHALL get the info text and SHALL keep the toll question open.

#### Scenario: A new origin

- **WHEN** the toll question is open and the user shares a location
- **THEN** the bot sends `Ahora envíame el destino.`, and the next location is the destination

#### Scenario: Typed coordinates

- **WHEN** the toll question is open and the user types `40.4168, -3.7038`
- **THEN** the bot sends `Ahora envíame el destino.`

#### Scenario: Other text

- **WHEN** the toll question is open and the user types `hola`
- **THEN** the bot sends the info text, and a press on `No` still sends the fuel question

### Requirement: An old toll button changes nothing

A press on a toll question that is not the open toll question of the user SHALL change no journey and SHALL send no fuel question. The bot SHALL remove the buttons of that message and send `Esta pregunta ha caducado.`

#### Scenario: A second press

- **WHEN** the user presses `No` and then `Sí (-44 min)` on the same message
- **THEN** the bot sends `Esta pregunta ha caducado.`, and the search excludes tolls

#### Scenario: A toll button after /reiniciar

- **WHEN** the user sends `/reiniciar` and then presses `No`
- **THEN** the bot sends `Esta pregunta ha caducado.`, and no fuel question is sent
