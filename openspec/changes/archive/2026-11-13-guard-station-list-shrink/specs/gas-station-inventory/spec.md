# Spec Delta

## ADDED Requirements

### Requirement: A list much shorter than the store changes nothing

When the store holds stations, a run SHALL count the valid stations of the list. When that count is less than 90 % of the stored count, the run SHALL NOT change the store, SHALL log both counts, and SHALL exit with a non-zero status. An empty store SHALL accept any list with at least one valid station.

#### Scenario: A truncated list

- **GIVEN** a store with 100 stations
- **WHEN** the list gives 89 valid stations
- **THEN** the run exits with a non-zero status, every stored row is unchanged, and the log names 89 and 100

#### Scenario: A list at the limit

- **GIVEN** a store with 100 stations
- **WHEN** the list gives 90 valid stations
- **THEN** the run exits with the status 0 and the store holds those 90 stations

#### Scenario: Many entries that cannot be read

- **GIVEN** a store with 100 stations
- **WHEN** the list has 100 entries and 11 of them are skipped
- **THEN** the run exits with a non-zero status and every stored row is unchanged

#### Scenario: The first run

- **GIVEN** an empty store
- **WHEN** the list gives 2 valid stations
- **THEN** the run exits with the status 0 and the store holds those 2 stations
