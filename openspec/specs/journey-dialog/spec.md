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

The bot SHALL keep the journey of each user in memory. The first location SHALL be the origin, and the bot SHALL send `Ahora envíame el destino.` The second location SHALL be the destination, and the bot SHALL send `¿Cuántos litros de combustible te quedan?` The next valid liters answer SHALL start the refuel search.

#### Scenario: A complete journey

- **WHEN** a user with a car sends a location, a second location, and then `10`
- **THEN** the bot sends `Ahora envíame el destino.`, then `¿Cuántos litros de combustible te quedan?`, then the answer of the refuel search for 10 L

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

### Requirement: The liters are a number from 0 to the tank volume

When the fuel question is open, the bot SHALL read typed text as liters before it tries to read a location. The liters SHALL be a number from 0 to the tank volume of the car, with a point or a comma as the decimal separator. Any other text SHALL make the bot send `Los litros deben ser un número de 0 a <volume>, por ejemplo 12,5. Escríbelo de nuevo.`, where `<volume>` is the tank volume.

#### Scenario: A decimal comma

- **WHEN** the fuel question is open and the user types `12,5`
- **THEN** the search starts with 12.5 L

#### Scenario: Too many liters

- **GIVEN** the tank volume of the car is 50
- **WHEN** the fuel question is open and the user types `60`
- **THEN** the bot sends `Los litros deben ser un número de 0 a 50, por ejemplo 12,5. Escríbelo de nuevo.`, and the fuel question stays open

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

When the fuel lasts to the destination, the bot SHALL send `No necesitas repostar: llegarás con <liters> L.`, where `<liters>` is the fuel left at the destination rounded down to a whole number.

#### Scenario: Enough fuel

- **WHEN** the search says 12.7 L are left at the destination
- **THEN** the bot sends `No necesitas repostar: llegarás con 12 L.`

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

When the router does not answer or answers with an error, the bot SHALL send `No he podido calcular la ruta. Lo siento mucho 😞` and SHALL keep the fuel question open. When the router finds no route between the origin and the destination, the bot SHALL send `No encuentro una ruta por carretera entre el origen y el destino. Envíame tu ubicación actual.` and SHALL forget the journey.

#### Scenario: The router is down

- **WHEN** the user answers the fuel question and `osrm` does not answer
- **THEN** the bot sends `No he podido calcular la ruta. Lo siento mucho 😞`, and the next `10` starts the search again
