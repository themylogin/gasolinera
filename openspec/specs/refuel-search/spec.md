# refuel-search Specification

## Purpose

Finds where on a route the tank of a car runs low, and gives the 10 stations near that point that sell the fuel of the car, with the lowest cost of fuel and time first, and with the road distance, the detour, and the arrival time of each.

## Requirements

### Requirement: The search follows the fastest route of the graph

The search SHALL ask `osrm` for the driving route from the origin to the destination, with the distance and the duration of each segment.

#### Scenario: The planned route

- **WHEN** a search starts
- **THEN** it requests one route from the origin to the destination, before any detour

### Requirement: Router durations are corrected by TIME_MULTIPLIER

Each duration that the search takes from the router SHALL be multiplied by `TIME_MULTIPLIER`. When `TIME_MULTIPLIER` is unset or empty, its value SHALL be `0.933`.

#### Scenario: The default value

- **WHEN** `TIME_MULTIPLIER` is not set and the router gives a leg 3,000 s
- **THEN** the search uses 2,799 s for that leg

### Requirement: The speed of a segment uses the corrected duration

The speed of a segment SHALL be its distance divided by its corrected duration, in km/h. A segment with a duration of 0 SHALL use the consumption at 80 km/h.

#### Scenario: The correction makes a segment faster

- **GIVEN** `TIME_MULTIPLIER` is `0.9`
- **WHEN** a segment is 1,000 m long and the router gives it 40 s
- **THEN** its speed is 100 km/h

### Requirement: The consumption at a speed comes from the two car consumptions

Below 80 km/h, the consumption SHALL be the consumption at 80 km/h. At 80 km/h and above, it SHALL be on the curve `a + b × v²` through `(80, consume_80)` and `(120, consume_120)`. The curve SHALL also apply above 120 km/h.

#### Scenario: A speed between the two

- **GIVEN** `consume_80` is 6 and `consume_120` is 8
- **WHEN** the speed is 100 km/h
- **THEN** the consumption is 6.9 L/100 km

#### Scenario: A fast speed

- **GIVEN** `consume_80` is 6 and `consume_120` is 8
- **WHEN** the speed is 130 km/h
- **THEN** the consumption is 8.625 L/100 km

#### Scenario: A slow speed

- **GIVEN** `consume_80` is 6
- **WHEN** the speed is 50 km/h
- **THEN** the consumption is 6 L/100 km

### Requirement: The search point is where the tank first holds 5 L or less

The search SHALL follow the route from the origin and subtract the fuel of each segment: its distance in km multiplied by its consumption, divided by 100. The search point SHALL be the first route point where 5 L or less are left. When the tank holds 5 L or less at the origin, the search point SHALL be the origin.

#### Scenario: The tank reaches 5 L on the route

- **GIVEN** a route of 10 segments of 10 km at 120 km/h, and `consume_120` is 10
- **WHEN** the tank holds 10 L
- **THEN** the search point is the end of the fifth segment

#### Scenario: Low fuel at the origin

- **WHEN** the tank holds 5 L
- **THEN** the search point is the origin

### Requirement: No stop is needed when the fuel lasts

With fuel, when more than 5 L are left at the destination, the search SHALL answer that no stop is needed, with the fuel left. With a range, when more than the reserve is left at the destination, the search SHALL answer that no stop is needed, with the range left. In both cases it SHALL then read no station and request no detour.

#### Scenario: A short trip

- **WHEN** the route uses 3 L and the tank holds 20 L
- **THEN** the answer is that no stop is needed with 17 L left, and no detour is requested

#### Scenario: A short trip with a range

- **GIVEN** a reserve of 50 km
- **WHEN** the route is 100 km long and the range is 183.4 km
- **THEN** the answer is that no stop is needed with 83.4 km left, and no detour is requested

#### Scenario: A range that leaves only the reserve

- **GIVEN** a reserve of 50 km
- **WHEN** the route is 100 km long and the range is 150 km
- **THEN** a stop is needed

### Requirement: The candidates are the 30 nearest stations that sell the fuel group

The candidates SHALL be the stations within 50 km of the search point, by great-circle distance, that have a price in the fuel group of the car, as `fuel-groups` defines it. The search SHALL keep the 30 nearest, and the lower station id when two are at the same distance.

#### Scenario: A station without the fuel

- **GIVEN** a car with the fuel group `diesel`
- **WHEN** a station 2 km from the search point sells only `Precio Gasoleo B`
- **THEN** that station is not a candidate

#### Scenario: A station too far

- **WHEN** a station that sells the fuel is 51 km from the search point
- **THEN** that station is not a candidate

### Requirement: Each candidate gets a detour through it

For each candidate, the search SHALL request the route from the origin through the station to the destination. The first leg SHALL give the road distance and the corrected driving time from the origin to the station. The detour time SHALL be the corrected duration of that route minus the corrected duration of the planned route. The search SHALL have no more than four detour requests open at the same time.

#### Scenario: The detour of a station

- **GIVEN** `TIME_MULTIPLIER` is `0.9`
- **WHEN** the router gives the planned route 10,000 s, and the route through a station 10,300 s with a first leg of 4,000 s and 150 km
- **THEN** the station has a detour of 270 s, a driving time of 3,600 s, and a distance of 150 km

#### Scenario: A station that the router cannot reach

- **WHEN** the router finds no route through one candidate
- **THEN** the answer does not list that candidate, and lists the others

### Requirement: The stop fills the tank

With fuel, the liters of a stop SHALL be the tank volume of the car minus the fuel left at the search point. With a range, they SHALL be the tank volume minus 5 L.

#### Scenario: A stop at 5 L

- **GIVEN** the tank volume is 50
- **WHEN** the fuel left at the search point is 5 L
- **THEN** the stop buys 45 L

#### Scenario: A stop from a range

- **GIVEN** the tank volume is 50
- **WHEN** the search started from a range
- **THEN** the stop buys 45 L

### Requirement: The cost of a stop is the fuel and the time

The cost of a candidate SHALL be the liters of the stop multiplied by its price, plus the detour time in hours multiplied by the value of time of the car. The price SHALL be the price that `fuel-groups` gives for the group at the station, with the field that gives it.

#### Scenario: The two parts

- **GIVEN** the value of time is 20 €/h, and the stop buys 45 L
- **WHEN** a station sells at 1.800 and its detour time is 600 s
- **THEN** its cost is 84.33 €, rounded to two decimals

#### Scenario: Time that costs nothing

- **GIVEN** the value of time is 0 €/h
- **WHEN** station A sells at 1.689 with a detour of 1,800 s, and station B sells at 1.699 with a detour of 60 s
- **THEN** A comes before B

### Requirement: The answer lists the 10 stops with the lowest cost

The answer SHALL list up to 10 candidates, ordered by cost and then by station id, from the lowest cost. The answer SHALL also give the liters of the stop.

#### Scenario: The cost decides the order, not the price

- **GIVEN** the value of time is 20 €/h, and the stop buys 45 L
- **WHEN** station A sells at 1.800 with a detour of 600 s, and station B sells at 1.750 with a detour of 1,800 s
- **THEN** A comes before B, because A costs 84.33 € and B costs 88.75 €

#### Scenario: More than 10 candidates

- **WHEN** 30 candidates have a detour
- **THEN** the answer lists 10 stations

### Requirement: Each listed station has an arrival time and an opening state

The arrival time at a station SHALL be the time the search started plus the driving time from the origin to the station. The opening state SHALL be the state that `opening-hours` gives for the `Horario` of the station at that arrival time, in the time zone of the station.

#### Scenario: The arrival time

- **WHEN** the search starts at 18:00 UTC and the driving time to a station is 5,400 s
- **THEN** the arrival time at that station is 19:30 UTC

### Requirement: The time zone of a station comes from its province

A station in the province `PALMAS (LAS)` or `SANTA CRUZ DE TENERIFE` SHALL use `Atlantic/Canary`. Every other station SHALL use `Europe/Madrid`.

#### Scenario: A station in Tenerife

- **WHEN** a station in `SANTA CRUZ DE TENERIFE` is reached at 20:30 UTC on 2026-11-07
- **THEN** its local arrival time is 20:30

#### Scenario: A station in Madrid

- **WHEN** a station in `MADRID` is reached at 20:30 UTC on 2026-11-07
- **THEN** its local arrival time is 21:30

### Requirement: Each listed station has a Google Maps link

The link of a station SHALL be `https://www.google.com/maps/search/?api=1&query=<latitude>%2C<longitude>`, with six decimals for each value.

#### Scenario: The link

- **WHEN** a station is at latitude 39.211417 and longitude -1.539167
- **THEN** its link is `https://www.google.com/maps/search/?api=1&query=39.211417%2C-1.539167`

### Requirement: A search starts from the fuel or from the range

A search SHALL start either from the fuel in the tank, in liters, or from the range of the car, in kilometers. A range SHALL NOT be converted to fuel.

#### Scenario: A search from a range

- **WHEN** a search starts with a range of 120 km
- **THEN** it uses no consumption to place the search point

### Requirement: With a range, the search point is where the range reaches the reserve

With a range, the search SHALL follow the route from the origin and subtract the distance of each segment from the range. The search point SHALL be the first route point where the range left is the reserve of the car or less. When the range is the reserve or less at the origin, the search point SHALL be the origin.

#### Scenario: The range reaches the reserve on the route

- **GIVEN** a route of 10 segments of 10 km, and a reserve of 50 km
- **WHEN** the range is 80 km
- **THEN** the search point is the end of the third segment

#### Scenario: A range below the reserve

- **GIVEN** a reserve of 50 km
- **WHEN** the range is 40 km
- **THEN** the search point is the origin
