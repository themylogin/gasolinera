# routing-service Specification

## Purpose

Builds a road graph of Spain from the OpenStreetMap extract and serves car routes from it through one OSRM query service.

## Requirements

### Requirement: The extract is the Geofabrik extract of Spain

The `download_pbf` step SHALL download `https://download.geofabrik.de/europe/spain-latest.osm.pbf` to `data/spain-latest.osm.pbf`. The step SHALL write to a temporary name and rename the file only on success.

#### Scenario: A fresh download

- **WHEN** `make download_pbf` runs and `data/spain-latest.osm.pbf` is absent
- **THEN** the extract is downloaded and is present at `data/spain-latest.osm.pbf`

#### Scenario: An interrupted download

- **WHEN** the download stops before it completes
- **THEN** `data/spain-latest.osm.pbf` does not exist, and the next run continues the transfer

### Requirement: The graph uses the default car profile

The `setup_osrm` step SHALL build the graph with the `car.lua` profile that the OSRM image contains. The step SHALL NOT change that profile.

#### Scenario: The profile is unchanged

- **WHEN** the graph is built
- **THEN** `osrm-extract` reads `/opt/car.lua` from the image, with no copy and no patch

### Requirement: The graph uses the multi-level Dijkstra pipeline

The `setup_osrm` step SHALL run `osrm-extract`, `osrm-partition`, and `osrm-customize`. The query service SHALL serve the graph with the `mld` algorithm.

#### Scenario: The graph is complete

- **WHEN** `setup_osrm` completes
- **THEN** `OSRM_PATH` holds the `spain-latest.osrm*` files and a stamp file that marks the graph as complete

### Requirement: The graph location comes from .env

The graph SHALL be stored at the absolute path that `OSRM_PATH` in `.env` names. Every step that reads or writes the graph SHALL stop with a clear message when `OSRM_PATH` is unset, empty, or relative.

#### Scenario: OSRM_PATH is unset

- **WHEN** `OSRM_PATH` is unset or empty and `make setup_osrm` runs
- **THEN** the step stops before it writes a file and names `OSRM_PATH` in its message

#### Scenario: OSRM_PATH is relative

- **WHEN** `OSRM_PATH` is `osrm/spain`
- **THEN** the step stops and tells the operator to use an absolute path

### Requirement: The build checks free disk space before preprocessing

The `setup_osrm` step SHALL stop before `osrm-extract` when `OSRM_PATH` has less than 10 GB free.

#### Scenario: Not enough disk

- **WHEN** `OSRM_PATH` has 6 GB free and `setup_osrm` runs
- **THEN** the step stops before `osrm-extract` and reports the free space and the 10 GB need

### Requirement: Steps do not repeat completed work

A step SHALL be skipped when its output exists. A newer extract SHALL NOT start a new graph build on its own.

#### Scenario: The graph exists

- **WHEN** the stamp file exists and `make setup_osrm` runs
- **THEN** no preprocessing runs

#### Scenario: The extract is newer than the graph

- **WHEN** the modification time of the extract is newer than the stamp file
- **THEN** `setup_osrm` is still skipped

### Requirement: The extract is not duplicated permanently

The copy of the extract under `OSRM_PATH` SHALL exist only during preprocessing. The extract under `data/` SHALL remain.

#### Scenario: After preprocessing

- **WHEN** `setup_osrm` completes
- **THEN** no `.osm.pbf` file is under `OSRM_PATH`, and `data/spain-latest.osm.pbf` is present

### Requirement: A rebuild starts from an empty graph directory

Before preprocessing, `setup_osrm` SHALL remove every `spain-latest.osrm*` file under `OSRM_PATH`. After preprocessing, it SHALL restart the `osrm` service.

#### Scenario: A killed run left part of a graph

- **WHEN** a previous run stopped during `osrm-partition` and `setup_osrm` runs again
- **THEN** the old files are removed first, and the new graph contains no file from the old run

#### Scenario: The service is running during a rebuild

- **WHEN** `osrm` is running and `setup_osrm` completes
- **THEN** `osrm` restarts and serves the new graph

### Requirement: One named query service

Compose SHALL define one long-running service, `osrm`, that serves the graph from `OSRM_PATH`. Other containers SHALL reach it at `http://osrm:5000` on the Compose network. The service SHALL publish no host port.

#### Scenario: A route request from another container

- **WHEN** a container on the Compose network requests `http://osrm:5000/route/v1/driving/-3.70,40.42;2.17,41.39`
- **THEN** the service returns a route with `"code": "Ok"`

#### Scenario: No host port

- **WHEN** the service runs
- **THEN** no host port is bound for it

### Requirement: Removing the graph keeps the extract

`make clean-osrm` SHALL remove the graph files and the stamp file under `OSRM_PATH`. It SHALL keep `data/spain-latest.osm.pbf`.

#### Scenario: Clean the graph

- **WHEN** `make clean-osrm` runs
- **THEN** `OSRM_PATH` holds no `spain-latest.osrm*` file and no stamp file, and the extract under `data/` is present
