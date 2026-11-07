# Tasks

## 1. Project skeleton

- [x] 1.1 Create `.gitignore` (`/.idea/`, `.env`, `/data/*.osm.pbf`, `docker-compose.override.yml`, `__pycache__/`) and `.dockerignore` (deny all, allow `alembic`, `alembic.ini`, `gasolinera`, `requirements.txt`). Verify that both files exist.
- [x] 1.2 Create `data/.gitkeep` and the package `gasolinera/__init__.py`. Verify that both files exist.
- [x] 1.3 Copy `french_tolls/.claude/output-styles/ste.md` to `gasolinera/.claude/output-styles/ste.md`. Verify with `diff` that the two files are equal.

## 2. Dependencies and image

- [x] 2.1 Create `pyproject.toml` with name `gasolinera`, `requires-python = ">=3.11"`, and dependencies `aiosqlite`, `alembic`, `pytest`, `python-telegram-bot~=21.0`, `SQLAlchemy[asyncio]>=2`. Verify that it parses with `python3 -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"`.
- [x] 2.2 Create the `Dockerfile` from `french_tolls/Dockerfile`: bookworm-slim, venv at `/opt/venv`, copy `gasolinera/`, `alembic.ini`, `alembic/`, default command `python3 -m gasolinera.bot`. Verify that the file names no `french_tolls` path.
- [x] 2.3 Create the `Makefile` header: `SHELL`, `.DELETE_ON_ERROR`, `-include .env`, `export`, `DOCKER ?= docker`, `COMPOSE ?= $(DOCKER) compose`, `HOST_USER`, and the `requirements` target from `french_tolls`. Run `make requirements` and verify that `requirements.txt` pins every package with a `# via` line.
- [x] 2.4 Run `make requirements` a second time and verify that `requirements.txt` does not change.

## 3. Configuration

- [x] 3.1 Create `gasolinera/config.py` with a frozen `Config` dataclass: `telegram_bot_token`, `log_level` (default `INFO`). Verify with `docker compose run --rm tests python3 -c "from gasolinera.config import config; print(config)"` after group 4 builds the image.
- [x] 3.2 Create `.env.example` with `OSRM_PATH`, `TELEGRAM_BOT_TOKEN`, `LOG_LEVEL`, each with a comment. Verify that `grep -c '=' .env.example` prints 3.

## 4. Runtime store

- [x] 4.1 Create `gasolinera/models.py` with `Base(DeclarativeBase)` and no model.
- [x] 4.2 Create `gasolinera/db.py`: async engine on `sqlite+aiosqlite:////cache/database.db`, WAL on connect, `Session = async_sessionmaker(engine, expire_on_commit=False)`.
- [x] 4.3 Create `alembic.ini` with the dated `file_template` and `sqlalchemy.url = sqlite:////cache/database.db`. Create `alembic/env.py` (target `Base.metadata`, `render_as_batch=True`, no `include_object`) and `alembic/script.py.mako` from `french_tolls`.
- [x] 4.4 Generate the baseline revision with `alembic revision -m baseline` in a container. Verify that its filename is `<YYYY-MM-DD_HH-MM>_baseline.py` and that `upgrade()` and `downgrade()` are `pass`.
- [x] 4.5 Add the `migrate` service (profiles `app`, `test`) and the volume `cache` to `docker-compose.yml`. Add the `tests` service (profile `test`, `tmpfs: /cache`). Add the `test` target to the `Makefile`.
- [x] 4.6 Write `gasolinera/tests/test_store.py`: a fresh upgrade gives only `alembic_version` at the baseline id, a second upgrade changes nothing, and `PRAGMA journal_mode` through `db.Session` returns `wal`. Verify that `make test` passes.

## 5. Telegram bot

- [x] 5.1 Create `gasolinera/bot.py` with `build(token)` that returns an `Application` with no handler, and `main()` that exits with `gasolinera: cannot start: TELEGRAM_BOT_TOKEN is not set` for an empty token, else calls `run_polling()`.
- [x] 5.2 Write `gasolinera/tests/test_bot.py`: `build("123:abc").handlers` is empty, and `main()` with an empty token raises `SystemExit` with the literal message. Verify that `make test` passes.
- [x] 5.3 Add the `bot` service (profile `app`, `env_file: .env`, depends on `migrate` with `service_completed_successfully`). Add the `bot` target with the token check, and the `down` target. Verify that `make bot` with an empty token fails before Compose runs and names `TELEGRAM_BOT_TOKEN`.

## 6. Routing service

- [x] 6.1 Add the services `osrm` (no profile, `--algorithm mld`, `restart: always`, no `ports`), `osrm-tools` (profile `tools`), and `download` (`curlimages/curl:8.23.0`, profile `tools`, mounts `./data`). Use the bind mount `${OSRM_PATH:-/OSRM_PATH-is-unset}` with `create_host_path: false`. Verify that `docker compose config` succeeds with no `.env`.
- [x] 6.2 Add `guard-osrm-path` to the `Makefile`. Verify that `make setup_osrm` stops with a message that names `OSRM_PATH` when it is unset, and when it is `osrm/spain`.
- [x] 6.3 Add `download_pbf`: download to `data/spain-latest.osm.pbf.part` with `--fail --location --retry 3 --continue-at -`, then rename. Verify that a second `make download_pbf` downloads nothing.
- [x] 6.4 Add `setup_osrm`: remove old `spain-latest.osrm*` files, check 10 GB free, hard-link the extract into `OSRM_PATH`, run `osrm-extract -p /opt/car.lua`, `osrm-partition`, `osrm-customize`, remove the staged extract, restart `osrm`, touch `.setup.stamp`. Make the extract order-only. Verify that a second `make setup_osrm` runs no preprocessing, also after `touch data/spain-latest.osm.pbf`.
- [x] 6.5 Add `all` (`download_pbf setup_osrm`), `osrm` (`compose up -d osrm`), and `clean-osrm`. Verify that `make clean-osrm` removes the graph and the stamp and keeps the extract.

## 7. Documentation and integration checks

- [x] 7.1 Write `README.md`: prerequisites (Docker, Compose, make, 12 GB RAM, 10 GB disk), `cp .env.example .env`, `make all`, `make osrm`, `make bot`, `make down`, `make test`, `make requirements`, and `DOCKER="sudo -n docker"`. Verify that each command in it exists as a `Makefile` target.
- [x] 7.2 On a fresh checkout with a valid `.env`, run `make all` and `make osrm`. Verify that `docker compose port osrm 5000` shows no host binding, and that a container on the network gets `"code": "Ok"` from `http://osrm:5000/route/v1/driving/-3.70,40.42;2.17,41.39`. Verify that no `.osm.pbf` is under `OSRM_PATH`.
- [ ] 7.3 Run `make bot` with a valid token. Verify that `migrate` exits with 0, `bot` keeps running, and a message to the bot gets no reply.
- [x] 7.4 Verify that every file under `data/` and `OSRM_PATH` belongs to the operator, and that `grep -ri french_tolls` outside `.claude/` finds nothing.
