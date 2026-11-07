# Spec Delta

## MODIFIED Requirements

### Requirement: Every persisted table is declared in one place

The application SHALL declare every table it reads or writes as a model, in one module. The store SHALL have exactly two application tables: the gas stations, with one geographic index, and the cars of the bot users. SQLite keeps internal tables for that index, and they are part of the index.

#### Scenario: The tables of a fresh store

- **WHEN** the schema is applied to a store that does not exist
- **THEN** the store contains `alembic_version`, `gas_station`, the index `gas_station_area` with its internal tables, `car`, and no other table
