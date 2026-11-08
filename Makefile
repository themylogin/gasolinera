SHELL := /bin/bash
.DELETE_ON_ERROR:

# A missing .env is not fatal here: the guards print a clearer message.
-include .env
export

DOCKER  ?= docker
COMPOSE ?= $(DOCKER) compose

PBF_URL := https://download.geofabrik.de/europe/spain-latest.osm.pbf
PBF     := data/spain-latest.osm.pbf

OSRM_DIR   := $(strip $(OSRM_PATH))
OSRM_STAMP := $(OSRM_DIR)/.setup.stamp

MIN_FREE_GB := 10

# Containers write into bind mounts. Without this, every output is owned by root.
HOST_USER := $(shell id -u):$(shell id -g)

.PHONY: all download_pbf setup_osrm guard-osrm-path osrm clean-osrm \
        requirements test bot down gas-stations gauge-image

all: guard-osrm-path download_pbf setup_osrm

# Without this, an unset OSRM_PATH turns $(OSRM_STAMP) into /.setup.stamp.
guard-osrm-path:
	@if [ -z "$(OSRM_DIR)" ]; then \
	    echo "ERROR: OSRM_PATH is unset or empty."; \
	    echo "       Copy .env.example to .env and point OSRM_PATH at an absolute"; \
	    echo "       path outside this repository with ~$(MIN_FREE_GB) GB free."; \
	    exit 1; \
	fi
	@case "$(OSRM_DIR)" in \
	    /*) ;; \
	    *)  echo "ERROR: OSRM_PATH must be an absolute path (got '$(OSRM_DIR)')."; \
	        exit 1;; \
	esac

download_pbf: $(PBF)

# A temporary name, so that an interrupted transfer never passes the existence check.
$(PBF):
	$(COMPOSE) run --rm --no-TTY --user $(HOST_USER) download \
	    --fail --location --retry 3 --continue-at - \
	    --output /data/spain-latest.osm.pbf.part "$(PBF_URL)"
	mv $@.part $@

setup_osrm: guard-osrm-path $(OSRM_STAMP)

# The extract is order-only: a new download must not start a rebuild by itself.
#
# osrm-routed maps the graph at startup, and a running container keeps the old
# graph after its files are replaced. So the service restarts at the end.
$(OSRM_STAMP): | $(PBF)
	rm -f "$(OSRM_DIR)"/spain-latest.osrm* "$(OSRM_DIR)"/*.osm.pbf
	mkdir -p "$(OSRM_DIR)"
	@free_gb=$$(df -Pk "$(OSRM_DIR)" | awk 'NR==2 {print int($$4/1024/1024)}'); \
	if [ "$$free_gb" -lt $(MIN_FREE_GB) ]; then \
	    echo "ERROR: only $${free_gb} GB free at $(OSRM_DIR); need ~$(MIN_FREE_GB) GB."; \
	    exit 1; \
	fi
	cp -l $(PBF) "$(OSRM_DIR)/spain-latest.osm.pbf" 2>/dev/null \
	    || cp $(PBF) "$(OSRM_DIR)/spain-latest.osm.pbf"
	$(COMPOSE) run --rm --no-TTY --user $(HOST_USER) osrm-tools \
	    osrm-extract -p /opt/car.lua /osrm/spain-latest.osm.pbf
	$(COMPOSE) run --rm --no-TTY --user $(HOST_USER) osrm-tools \
	    osrm-partition /osrm/spain-latest.osrm
	$(COMPOSE) run --rm --no-TTY --user $(HOST_USER) osrm-tools \
	    osrm-customize /osrm/spain-latest.osrm
	rm -f "$(OSRM_DIR)/spain-latest.osm.pbf"
	$(COMPOSE) restart osrm 2>/dev/null || true
	touch $@

osrm: guard-osrm-path
	$(COMPOSE) up -d osrm

clean-osrm: guard-osrm-path
	$(COMPOSE) stop osrm || true
	rm -f "$(OSRM_DIR)"/spain-latest.osrm* "$(OSRM_DIR)"/*.osm.pbf "$(OSRM_STAMP)"

# Resolves in a container for the Python of Debian bookworm, which the image runs.
# uv keeps a pin that still satisfies pyproject.toml, so the committed list goes in
# too: without it, each run resolves against the index of that day.
# The output goes to a new file first, because a redirection to requirements.txt
# empties it before the container reads it.
requirements:
	touch requirements.txt
	$(DOCKER) run --rm -v "$$(pwd)/pyproject.toml:/in/pyproject.toml:ro" \
	    -v "$$(pwd)/requirements.txt:/in/requirements.txt:ro" \
	    ghcr.io/astral-sh/uv:python3.11-bookworm-slim \
	    sh -c 'mkdir -p /build && cp /in/pyproject.toml /in/requirements.txt /build/ \
	           && cd /build \
	           && uv pip compile --python-version 3.11.2 pyproject.toml -o requirements.txt \
	           >/dev/null 2>&1 \
	           && cat requirements.txt' > requirements.txt.new
	mv requirements.txt.new requirements.txt

# No prerequisites: the suite needs no graph and no .env.
test:
	$(COMPOSE) --profile test run --rm --no-TTY --build tests

bot:
	@if [ -z "$(TELEGRAM_BOT_TOKEN)" ]; then \
	    echo "ERROR: TELEGRAM_BOT_TOKEN is unset or empty."; \
	    echo "       Copy .env.example to .env and set it to the token BotFather"; \
	    echo "       issued. The bot polls Telegram and cannot start without one."; \
	    exit 1; \
	fi
	$(COMPOSE) --profile app up -d --build bot

down:
	$(COMPOSE) --profile app --profile tools --profile test --profile gas-stations down

gas-stations:
	$(COMPOSE) --profile gas-stations run --rm --no-TTY --build gas-stations

# Pillow runs in a throwaway container, so the app image needs no image library.
gauge-image:
	$(DOCKER) run --rm --user $(HOST_USER) -e UV_CACHE_DIR=/tmp/uv -v "$$(pwd):/work" -w /work \
	    ghcr.io/astral-sh/uv:python3.11-bookworm-slim \
	    uv run --no-project --with pillow python gauge/render.py
