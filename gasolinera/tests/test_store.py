# -*- coding=utf-8 -*-
import asyncio
from pathlib import Path
import sqlite3
import subprocess

import pytest
from sqlalchemy import text

from .. import db

DATABASE = Path("/cache/database.db")


@pytest.fixture(autouse=True)
def no_store():
    for path in DATABASE.parent.glob("database.db*"):
        path.unlink()


def upgrade():
    subprocess.run(["alembic", "upgrade", "head"], cwd="/app", check=True)


def read_store():
    with sqlite3.connect(DATABASE) as connection:
        tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
        versions = [row[0] for row in connection.execute("SELECT version_num FROM alembic_version")]
    return tables, versions


def test_fresh_store_has_the_station_table_at_the_latest_revision():
    upgrade()

    assert read_store() == (
        [
            "alembic_version",
            "gas_station",
            "gas_station_area",
            "gas_station_area_rowid",
            "gas_station_area_node",
            "gas_station_area_parent",
            "car",
        ],
        ["df0c73903ae5"],
    )


def test_second_upgrade_changes_nothing():
    upgrade()
    before = read_store()

    upgrade()

    assert read_store() == before


def test_session_uses_wal():
    async def journal_mode():
        async with db.Session() as session:
            return (await session.execute(text("PRAGMA journal_mode"))).scalar_one()

    assert asyncio.run(journal_mode()) == "wal"


def test_only_a_revision_creates_a_virtual_table_or_a_trigger():
    sources = [
        path
        for path in Path("/app").rglob("*.py")
        if "tests" not in path.parts
        and any(statement in path.read_text() for statement in ("CREATE VIRTUAL TABLE", "CREATE TRIGGER"))
    ]

    assert [path.name for path in sources] == ["2026-11-07_19-40_gas_stations.py"]
