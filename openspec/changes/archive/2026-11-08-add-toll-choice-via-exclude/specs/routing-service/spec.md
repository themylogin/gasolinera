# Spec Delta

## ADDED Requirements

### Requirement: The query service routes without toll roads on request

The `osrm` service SHALL answer a route request with `exclude=toll` from the same graph. The answer SHALL use no way that the default car profile marks as a toll road. The graph SHALL need no rebuild and no second profile for this.

#### Scenario: Barcelona to Puigcerdà without tolls

- **WHEN** a container on the Compose network requests `http://osrm:5000/route/v1/driving/2.1734,41.3851;1.9280,42.4317?exclude=toll`
- **THEN** the service returns a route with `"code": "Ok"`, and its duration is longer than the duration of the same request without `exclude`

#### Scenario: Barcelona to Lleida without tolls

- **WHEN** a container on the Compose network requests the route from `2.1734,41.3851` to `0.6200,41.6176` with and without `exclude=toll`
- **THEN** both answers have the same geometry
