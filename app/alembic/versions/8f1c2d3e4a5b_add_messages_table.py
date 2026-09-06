"""Add messages table.

Revision ID: 8f1c2d3e4a5b
Revises: 6b63f8b0f211
Create Date: 2026-09-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f1c2d3e4a5b"
down_revision: Union[str, Sequence[str], None] = "6b63f8b0f211"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "messages" in inspector.get_table_names():
        return

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("sender_type", sa.String(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_auto_reply", sa.Boolean(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("needs_review", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_id", "messages", ["id"], unique=False)
    op.create_index("idx_conversation_id", "messages", ["conversation_id"], unique=False)
    op.create_index("idx_sender_id", "messages", ["sender_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_sender_id", table_name="messages")
    op.drop_index("idx_conversation_id", table_name="messages")
    op.drop_index("ix_messages_id", table_name="messages")
    op.drop_table("messages")
