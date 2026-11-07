# Design

## Context

`gasolinera/` holds only the OpenSpec setup. `french_tolls/` is the reference project. This design copies its structure and removes everything that is specific to tolls.

Parts that this change copies from `french_tolls`, in reduced form:

- `docker-compose.yml`: the OSRM service, the `migrate` run, the bot, the tool and test profiles.
- `Makefile`: the path guards, the existence-based steps, `DOCKER`/`COMPOSE` overrides, `HOST_USER`, `make test`, `make requirements`.
- `Dockerfile`: Debian bookworm, a virtual environment, pinned `requirements.txt`.
- `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`: dated revision filenames, batch mode.
- `<package>/config.py` and `<package>/db.py`: a frozen config dataclass, an async engine with WAL.
- `.env.example`, `.gitignore`, `.dockerignore`, `README.md`.
- `.claude/output-styles/ste.md`: the STE output style.

Parts that this change does not copy: the builder image, the profile patch, the second graph, the web service, nginx, the relay, the evaluation, and the integration suite.

## Goals / Non-Goals

**Goals:**

- A stack that starts with `make all` and `make bot` on a fresh host.
- The same conventions as `french_tolls`, so that code and habits move between the two projects.

**Non-Goals:**

- A shared library between the two projects. Each project keeps its own copy.
- A `builder` image. No step in this change runs Python on the host data.

## Decisions

### Layout

```
gasolinera/
├── .claude/output-styles/ste.md
├── .dockerignore  .env.example  .gitignore
├── Dockerfile  docker-compose.yml  Makefile  README.md
├── pyproject.toml  requirements.txt
├── alembic.ini
├── alembic/{env.py, script.py.mako, versions/<date>_baseline.py}
├── data/                       # the extract; git ignores *.osm.pbf
└── gasolinera/
    ├── __init__.py  config.py  db.py  models.py  bot.py
    └── tests/{__init__.py, test_bot.py, test_store.py}
```

The Python package has the name `gasolinera`, the same as the project. This matches `french_tolls/french_tolls`.

### Compose services

| Service | Image | Profile | Role |
| --- | --- | --- | --- |
| `osrm` | `ghcr.io/project-osrm/osrm-backend:26.8-debian` | none | `osrm-routed --algorithm mld /osrm/spain-latest.osrm` |
| `osrm-tools` | same | `tools` | runs `osrm-extract`, `osrm-partition`, `osrm-customize` |
| `download` | `curlimages/curl:8.23.0` | `tools` | downloads the extract into `./data` |
| `migrate` | local build | `app`, `test` | `alembic upgrade head` on volume `cache` |
| `bot` | local build | `app` | `python3 -m gasolinera.bot`, depends on `migrate` |
| `tests` | local build | `test` | `pytest` with a `tmpfs` at `/cache` |

`osrm` and `osrm-tools` bind-mount `${OSRM_PATH:-/OSRM_PATH-is-unset}` with `create_host_path: false`. An unset variable then fails at mount time with a readable path, not with a Compose parse error. This is the same pattern as `french_tolls`.

`osrm` has no profile, so a plain `docker compose up -d` starts only the router. This is the same as `french_tolls`.

Alternative: put `osrm` behind a profile. Rejected, because the router is the base of all later features.

### Build steps

`make all` runs `download_pbf` then `setup_osrm`. Both are existence-based. The extract is an order-only prerequisite of the stamp, so a new download does not start a rebuild. Without a patch file and a blacklist, the stamp has no normal prerequisites.

`download_pbf` runs `curl` in a `download` service on the image `curlimages/curl:8.23.0`. The OSRM image has no `curl` and no `wget`.

Alternative: keep a `builder` image only for `curl`. Rejected as too heavy for one command.

`setup_osrm` calls `osrm-extract -p /opt/car.lua`. It does not copy the profile out of the image, because nothing changes it.

The disk guard is 10 GB. The Spain extract is 1.5 GB. The MLD graph is 3.4 GB. The stage copy is a hard link when possible.

### The store

`models.py` declares `Base` and no model. `alembic/env.py` uses `Base.metadata`, so autogenerate works when the first table arrives.

The baseline revision has empty `upgrade()` and `downgrade()` functions. With it, a fresh store records a version from day one. Later revisions then have a parent.

Alternative: no revision until the first table. Rejected, because then `alembic_version` stays empty and the store records no version.

`db.py` creates the async engine on `sqlite+aiosqlite:////cache/database.db` and sets WAL on connect. Nothing uses `Session` yet. It is in this change so that the first feature that needs the store does not have to set up the engine.

### The bot

`bot.py` has `build(token)` and `main()`. `build` returns a `telegram.ext.Application` with no handler. `main` checks `TELEGRAM_BOT_TOKEN` and calls `run_polling()`.

The bot has no `post_init` and calls no `set_my_commands`, because it has no command to list.

`python-telegram-bot~=21.0` is the same bound as in `french_tolls`.

### Dependencies

`pyproject.toml` declares `aiosqlite`, `alembic`, `pytest`, `python-telegram-bot~=21.0`, `SQLAlchemy[asyncio]>=2`. SQLAlchemy 2.1 makes `greenlet` optional, and the async engine needs it, so the declaration asks for the `asyncio` extra. `make requirements` compiles them with `uv pip compile --python-version 3.11.2`, the Python of Debian bookworm.

### Tests

The suite has these tests:

- `test_bot.py`: `build("123:abc")` returns an application with no handler. `main()` with an empty token exits with the message that `telegram-bot` specifies.
- `test_store.py`: `alembic upgrade head` on an empty `/cache` gives only `alembic_version`, at the baseline revision. A second upgrade changes nothing. A session from `db.Session` reports `journal_mode` `wal`.

The `tests` service mounts a `tmpfs` at `/cache`. The store tests then use the real path that `alembic.ini` and `db.py` use.

The tests do not cover the routing-service scenarios. Those need the extract and a 10-minute build. The apply phase checks them by hand (group 7 of tasks.md).

### Make targets

`all`, `download_pbf`, `setup_osrm`, `osrm`, `bot`, `down`, `test`, `requirements`, `clean-osrm`, plus the guard `guard-osrm-path`.

`make osrm` starts the router. `make bot` checks the token and starts `bot`. `make down` stops the services of all profiles.

## Risks / Trade-offs

- [The OSRM image tag `26.8-debian` is also used by `french_tolls`] → Pin the same tag. Both projects then move to a new tag together.
- [A bot with no handlers still fetches updates] → Accept it. Telegram drops the updates after the bot confirms them, and the cost is one request per poll.
- [Preprocessing needs about 11 GB of RAM: the first build was killed on a 7 GB host] → The README states 12 GB.
- [Two copies of the same conventions drift apart] → Accept it. The projects are separate. A later change can extract shared parts if the drift becomes a problem.

## Migration Plan

There is no deployment to migrate. To roll back, delete the new files.
