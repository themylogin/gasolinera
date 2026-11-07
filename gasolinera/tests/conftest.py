# -*- coding=utf-8 -*-
import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .. import db


@pytest.fixture
def store(tmp_path, monkeypatch):
    db_path = tmp_path / "database.db"
    alembic_config = Config(Path(__file__).parents[2] / "alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(alembic_config, "head")

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setattr(db, "Session", async_sessionmaker(engine, expire_on_commit=False))
    yield db_path
    asyncio.run(engine.dispose())
