"""gas stations: the station table, its R*Tree index, and the triggers that keep the index

Revision ID: 255cb2d4557a
Revises: d13b3f5e580d
Create Date: 2026-11-07 19:40:56.712012

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "255cb2d4557a"
down_revision: Union[str, None] = "d13b3f5e580d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gas_station",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("postal_code", sa.Text(), nullable=False),
        sa.Column("locality", sa.Text(), nullable=False),
        sa.Column("municipality", sa.Text(), nullable=False),
        sa.Column("province", sa.Text(), nullable=False),
        sa.Column("opening_hours", sa.Text(), nullable=False),
        sa.Column("prices", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # The model layer cannot create a virtual table or a trigger, so these
    # statements are written by hand. runtime-store permits it here only.
    op.execute(
        "CREATE VIRTUAL TABLE gas_station_area USING rtree("
        "id, min_latitude, max_latitude, min_longitude, max_longitude)"
    )

    # WARNING: a batch revision that copies gas_station drops these triggers
    # together with the old table. Such a revision must create them again.
    op.execute(
        """
        CREATE TRIGGER gas_station_area_insert AFTER INSERT ON gas_station
        BEGIN
            INSERT INTO gas_station_area
            VALUES (new.id, new.latitude, new.latitude, new.longitude, new.longitude);
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER gas_station_area_update AFTER UPDATE OF id, latitude, longitude ON gas_station
        BEGIN
            DELETE FROM gas_station_area WHERE id = old.id;
            INSERT INTO gas_station_area
            VALUES (new.id, new.latitude, new.latitude, new.longitude, new.longitude);
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER gas_station_area_delete AFTER DELETE ON gas_station
        BEGIN
            DELETE FROM gas_station_area WHERE id = old.id;
        END
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER gas_station_area_delete")
    op.execute("DROP TRIGGER gas_station_area_update")
    op.execute("DROP TRIGGER gas_station_area_insert")
    op.execute("DROP TABLE gas_station_area")
    op.drop_table("gas_station")
