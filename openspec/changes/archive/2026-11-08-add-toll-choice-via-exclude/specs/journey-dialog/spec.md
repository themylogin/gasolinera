# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

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
