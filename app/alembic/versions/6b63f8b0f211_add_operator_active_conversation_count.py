"""add operator active conversation count

Revision ID: 6b63f8b0f211
Revises: d25a18bb1972
Create Date: 2026-04-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6b63f8b0f211"
down_revision: Union[str, Sequence[str], None] = "d25a18bb1972"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    users_columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    if "active_conversations_count" not in users_columns:
        op.add_column(
            "users",
            sa.Column("active_conversations_count", sa.Integer(), nullable=False, server_default="0"),
        )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("active_conversations_count", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "active_conversations_count")
