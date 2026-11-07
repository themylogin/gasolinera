"""baseline: no application tables

Revision ID: d13b3f5e580d
Revises:
Create Date: 2026-11-07 19:04:15.295786

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d13b3f5e580d"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
