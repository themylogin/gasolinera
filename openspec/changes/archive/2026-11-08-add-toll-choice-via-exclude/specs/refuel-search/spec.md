# Spec Delta

## MODIFIED Requirements

### Requirement: The search follows the fastest route of the graph

The search SHALL ask `osrm` for the driving route from the origin to the destination, with the distance and the duration of each segment. When the journey uses the toll-free route, the planned route and every detour request of the search SHALL exclude toll roads. Otherwise no request of the search SHALL exclude toll roads.

#### Scenario: The planned route

- **WHEN** a search starts
- **THEN** it requests one route from the origin to the destination, before any detour

#### Scenario: A toll-free search

- **GIVEN** the user pressed `No` on the toll question
- **WHEN** the search runs
- **THEN** the planned route and every route through a station exclude toll roads
