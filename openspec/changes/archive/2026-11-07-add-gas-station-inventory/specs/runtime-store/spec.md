# Spec Delta

## ADDED Requirements

### Requirement: Every persisted table is declared in one place

The application SHALL declare every table it reads or writes as a model, in one module. The store SHALL have exactly one application table, the gas stations, with one geographic index. SQLite keeps internal tables for that index, and they are part of the index.

#### Scenario: The tables of a fresh store

- **WHEN** the schema is applied to a store that does not exist
- **THEN** the store contains `alembic_version`, `gas_station`, the index `gas_station_area` with its internal tables, and no other table

### Requirement: A structure the models cannot create lives only in a revision

The geographic index is a virtual table, and triggers keep it equal to the station table. The model layer cannot create them. A hand-written statement SHALL create them inside a revision, and nowhere else. The index SHALL still be declared as a model, so that a query reaches it through the model.

#### Scenario: Hand-written statements

- **WHEN** the source is searched for statements that create a table, a virtual table, or a trigger
- **THEN** the only ones are in the revision that creates the geographic index and its triggers

## MODIFIED Requirements

### Requirement: The schema is versioned

The store SHALL record its schema version. A schema change SHALL be a revision. Applying the revisions to a store at the latest version SHALL change nothing.

#### Scenario: The version is recorded

- **WHEN** the schema is applied to a fresh store
- **THEN** the store names the latest revision as its version

#### Scenario: Applying twice changes nothing

- **WHEN** the schema is applied to a store at the latest version
- **THEN** no table or row changes

## REMOVED Requirements

### Requirement: The store has no application tables

**Reason**: The store now keeps the gas stations of `gas-station-inventory`.

**Migration**: The requirement "Every persisted table is declared in one place" lists the tables. The `migrate` run adds the station table to an existing store.
