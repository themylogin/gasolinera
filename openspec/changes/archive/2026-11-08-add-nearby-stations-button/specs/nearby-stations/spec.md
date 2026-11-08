# Spec Delta

## Purpose

Lists the gas stations nearest to the position of the user that sell the fuel of their car, nearest first, without a route.

## ADDED Requirements

### Requirement: The list holds the 10 nearest stations that sell the fuel group

The list SHALL hold the stations within 50 km of the position, by great-circle distance, that have a price in the fuel group of the car, as `fuel-groups` defines it. The list SHALL keep the 10 nearest. It SHALL request no route.

#### Scenario: A station without the fuel

- **GIVEN** a car with the fuel group `diesel`
- **WHEN** a station 1 km from the position sells only `Precio Gasoleo B`
- **THEN** that station is not in the list

#### Scenario: A station too far

- **WHEN** a station that sells the fuel is 51 km from the position
- **THEN** that station is not in the list

#### Scenario: More than 10 stations

- **WHEN** 12 stations that sell the fuel are within 50 km
- **THEN** the list holds the 10 nearest

### Requirement: The nearest station comes first

The list SHALL be in ascending order of distance from the position. When two stations are at the same distance, the station with the lower id SHALL come first.

#### Scenario: Two stations

- **WHEN** station A is 3.2 km and station B is 0.8 km from the position
- **THEN** B is number 1 and A is number 2

### Requirement: The list is one HTML message

The bot SHALL send the list in one HTML message without a link preview and without a header. The stations SHALL be numbered from 1, with an empty line between two stations.

#### Scenario: The first line

- **WHEN** the list holds 3 stations
- **THEN** the message starts with the first line of station 1, and the stations are numbered from 1 to 3

### Requirement: Each nearby station has two lines and an alert when needed

Each station SHALL have two lines:

1. its number and its name as a link to its Google Maps position, then ` · ` and the distance in km with one decimal and a comma;
2. the price with three decimals and a comma followed by ` €/L`.

The name SHALL be escaped and the link SHALL be built as for the refuel answer. An alert line SHALL follow only when the opening state now is not `open`.

#### Scenario: One open station

- **WHEN** the first station is `GALP`, with 1.499, 430 m from the position
- **THEN** its lines are `1. <a href="https://www.google.com/maps/search/?api=1&amp;query=…">GALP</a> · 0,4 km` and `1,499 €/L`, and it has no alert line

#### Scenario: A far station

- **WHEN** a station is 12.46 km from the position
- **THEN** its first line ends with `· 12,5 km`

### Requirement: The alert line uses the time of the press

The opening state SHALL be the state that `opening-hours` gives for the `Horario` of the station at the time of the press, in the time zone of the station. The alert line SHALL be:

- for closed: `⚠️ <b>Cerrada</b> a las <now>`;
- for closing soon: `⚠️ <b>Cierra pronto</b> a las <closing>`;
- for unknown: `⚠️ <b>Horario desconocido</b>`.

#### Scenario: Closed now

- **WHEN** the user presses the button at 22:41 in Madrid and a station in `MADRID` has the schedule `L-D: 07:00-22:00`
- **THEN** its alert line is `⚠️ <b>Cerrada</b> a las 22:41`

#### Scenario: Closing soon

- **WHEN** the user presses the button at 21:45 in Madrid and a station in `MADRID` has the schedule `L-D: 07:00-22:00`
- **THEN** its alert line is `⚠️ <b>Cierra pronto</b> a las 22:00`

### Requirement: An empty list is reported

When no station within 50 km sells the fuel group of the car, the bot SHALL send `Ninguna gasolinera vende <fuel> a menos de 50 km de tu ubicación.` `<fuel>` SHALL be the label of the fuel of the car.

#### Scenario: No diesel nearby

- **GIVEN** a car with the fuel `Diésel`
- **WHEN** no station within 50 km sells diesel
- **THEN** the bot sends `Ninguna gasolinera vende Diésel a menos de 50 km de tu ubicación.`
