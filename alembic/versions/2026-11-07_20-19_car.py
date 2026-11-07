"""car: the car of each Telegram user

Revision ID: f82ef6e766d8
Revises: 255cb2d4557a
Create Date: 2026-11-07 20:19:56.950358

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f82ef6e766d8"
down_revision: Union[str, None] = "255cb2d4557a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "car",
        sa.Column("telegram_user_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("tank_volume", sa.Integer(), nullable=False),
        sa.Column("fuel_type", sa.Text(), nullable=False),
        sa.Column("consume_80", sa.Float(), nullable=False),
        sa.Column("consume_120", sa.Float(), nullable=False),
        sa.Column("eur_per_hour", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("telegram_user_id"),
    )


def downgrade() -> None:
    op.drop_table("car")
