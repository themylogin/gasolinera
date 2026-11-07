# Spec Delta

## Purpose

Keeps the state the application carries between requests in one SQLite file, with a versioned schema that one run applies.

## ADDED Requirements

### Requirement: The store is one SQLite file on a named volume

The store SHALL be the file `/cache/database.db`. The file SHALL be on the Compose volume `cache`, so that it survives a container restart.

#### Scenario: The store survives a restart

- **WHEN** the `bot` container is removed and started again
- **THEN** `/cache/database.db` is the same file as before

### Requirement: The store has no application tables

The store SHALL contain no table other than the schema version record.

#### Scenario: A fresh store

- **WHEN** the schema is applied to a store that does not exist
- **THEN** the store contains the `alembic_version` table and no other table

### Requirement: The schema is versioned

The store SHALL record its schema version. A schema change SHALL be a revision. Applying the revisions to a store at the latest version SHALL change nothing.

#### Scenario: The version is recorded

- **WHEN** the schema is applied to a fresh store
- **THEN** the store names the baseline revision as its version

#### Scenario: Applying twice changes nothing

- **WHEN** the schema is applied to a store at the latest version
- **THEN** no table or row changes

### Requirement: Revision files sort in the order they were written

A revision filename SHALL start with the date and time it was written and SHALL end with its name. The identity of a revision SHALL be the id inside the file, not the filename.

#### Scenario: A new revision

- **WHEN** a revision named `baseline` is generated on 2026-11-07 at 19:30
- **THEN** its filename is `2026-11-07_19-30_baseline.py`

### Requirement: Exactly one process applies the schema

A one-shot `migrate` run SHALL apply the schema and exit. A service that uses the store SHALL NOT start until `migrate` completes with success. A serving process SHALL NOT create tables.

#### Scenario: The bot starts

- **WHEN** `make bot` runs
- **THEN** `migrate` runs and exits with status 0, and `bot` starts after it

#### Scenario: The migration fails

- **WHEN** `migrate` exits with a non-zero status
- **THEN** `bot` does not start

### Requirement: The store is reached without blocking the event loop

Every call that reads or writes the store SHALL be a coroutine and SHALL use an asynchronous SQLite driver. The store SHALL use the WAL journal mode.

#### Scenario: The journal mode

- **WHEN** a process opens the store
- **THEN** the journal mode of the connection is `wal`
