"""Allow AI messages without a user sender.

Revision ID: b1c2d3e4f5a6
Revises: 8f1c2d3e4a5b
Create Date: 2026-09-07 18:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "8f1c2d3e4a5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("messages") as batch_op:
        batch_op.alter_column(
            "sender_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("messages") as batch_op:
        batch_op.alter_column(
            "sender_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
