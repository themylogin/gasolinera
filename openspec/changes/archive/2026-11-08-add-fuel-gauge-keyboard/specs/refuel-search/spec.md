# Spec Delta

## ADDED Requirements

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

## MODIFIED Requirements

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
