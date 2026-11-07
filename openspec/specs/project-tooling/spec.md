# project-tooling Specification

## Purpose

Defines how Gasolinera is built, configured, and tested: all work in containers, configuration from `.env`, pinned dependencies, and one test command.

## Requirements

### Requirement: All work runs in containers

Every build step, service, and test SHALL run in a container. The host SHALL need only Docker, the Compose plugin, GNU make, and coreutils.

#### Scenario: A host without Python tools

- **WHEN** the host has no Python packages, no osmium, and no OSRM installed
- **THEN** `make all`, `make bot`, and `make test` succeed

### Requirement: The Docker command can be overridden

The Makefile SHALL read the Docker command from the variable `DOCKER`, with `docker` as the default value.

#### Scenario: No access to the Docker socket

- **WHEN** the operator runs `make test DOCKER="sudo -n docker"`
- **THEN** every container command uses `sudo -n docker`

### Requirement: Containers write files as the operator

A container that writes into `data/` or `OSRM_PATH` SHALL run as the user and group of the operator who runs `make`.

#### Scenario: Files after a build

- **WHEN** `make all` completes
- **THEN** the operator owns every file it wrote under `data/` and `OSRM_PATH`

### Requirement: Configuration comes from .env

The project SHALL read its configuration from `.env`. The file `.env.example` SHALL list every variable with a comment. Git SHALL ignore `.env`.

#### Scenario: A new checkout

- **WHEN** the operator runs `cp .env.example .env`
- **THEN** `.env` names `OSRM_PATH`, `TELEGRAM_BOT_TOKEN`, and `LOG_LEVEL`

### Requirement: Python dependencies are pinned

The application image SHALL install its Python dependencies from `requirements.txt` only. `make requirements` SHALL compile `requirements.txt` from `pyproject.toml` in a container, for the Python version of the image. The list SHALL pin every package, including transitive ones.

#### Scenario: The image build

- **WHEN** the application image is built
- **THEN** pip installs every package from `requirements.txt` into a virtual environment, and no Python package comes from the distribution

#### Scenario: The list reproduces

- **WHEN** `make requirements` runs on an unchanged `pyproject.toml`
- **THEN** `requirements.txt` does not change

### Requirement: One command runs the unit tests

`make test` SHALL run the unit test suite in a container. It SHALL need no `.env`, no graph, and no network access to Telegram. Its exit status SHALL be the status of the suite.

#### Scenario: A fresh checkout

- **WHEN** `make test` runs on a checkout with no `.env` and no graph
- **THEN** the suite runs and the target exits with the status of the suite

### Requirement: The README describes setup and run

`README.md` SHALL state the prerequisites, the configuration, the build command, the run commands, and the test command.

#### Scenario: A new operator

- **WHEN** an operator follows `README.md` from a fresh checkout
- **THEN** they build the graph, start the services, and run the tests with no other document
