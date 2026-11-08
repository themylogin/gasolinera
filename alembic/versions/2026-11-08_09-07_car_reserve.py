"""car_reserve: the reserve in km of each car, 50 for the cars stored before it

Revision ID: d449d7fdb4d1
Revises: f82ef6e766d8
Create Date: 2026-11-08 09:07:13.870885

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d449d7fdb4d1"
down_revision: Union[str, None] = "f82ef6e766d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("car", schema=None) as batch_op:
        batch_op.add_column(sa.Column("reserve_km", sa.Float(), server_default="50", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("car", schema=None) as batch_op:
        batch_op.drop_column("reserve_km")
