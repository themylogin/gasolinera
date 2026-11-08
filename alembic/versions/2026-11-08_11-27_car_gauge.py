"""car_gauge: the gauge of each car as its steps, 16 for the cars stored before it

Revision ID: df0c73903ae5
Revises: d449d7fdb4d1
Create Date: 2026-11-08 11:27:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "df0c73903ae5"
down_revision: Union[str, None] = "d449d7fdb4d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("car", schema=None) as batch_op:
        batch_op.add_column(sa.Column("gauge_steps", sa.Integer(), server_default="16", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("car", schema=None) as batch_op:
        batch_op.drop_column("gauge_steps")
