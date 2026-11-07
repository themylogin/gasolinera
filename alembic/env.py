# -*- coding=utf-8 -*-
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from gasolinera.models import Base

config = context.config

if config.config_file_name is not None:
    # The default disables every logger that exists already, which silences the
    # application when a test migrates in-process.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def include_object(object_, name, type_, reflected, compare_to):
    return not (type_ == "table" and name.startswith("gas_station_area"))


def run_migrations_offline():
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # SQLite cannot ALTER most things, so a column change copies the table.
        # Batch mode writes that copy. It is on from the first revision so that
        # the first such change does not discover it.
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    engine = create_engine(config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
