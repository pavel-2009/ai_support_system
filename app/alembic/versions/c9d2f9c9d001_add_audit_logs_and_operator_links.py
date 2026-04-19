"""add audit logs and operator links

Revision ID: c9d2f9c9d001
Revises: a1ee5ee8231c
Create Date: 2026-04-16 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c9d2f9c9d001"
down_revision: Union[str, Sequence[str], None] = "a1ee5ee8231c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "conversation_operator_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("operator_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
        sa.Column("unassigned_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["operator_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("conversation_operator_links", schema=None) as batch_op:
        batch_op.create_index(
            "idx_conversation_operator_active",
            ["conversation_id", "operator_id", "is_active"],
            unique=False,
        )
        batch_op.create_index(batch_op.f("ix_conversation_operator_links_id"), ["id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column(
            "from_status",
            sa.Enum(
                "OPEN",
                "WAITING_FOR_USER",
                "WAITING_FOR_OPERATOR",
                "ESCALATED",
                "PENDING_AI",
                "CLOSED",
                name="status",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "to_status",
            sa.Enum(
                "OPEN",
                "WAITING_FOR_USER",
                "WAITING_FOR_OPERATOR",
                "ESCALATED",
                "PENDING_AI",
                "CLOSED",
                name="status",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("audit_logs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_audit_logs_conversation_id"), ["conversation_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_audit_logs_id"), ["id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("audit_logs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_audit_logs_id"))
        batch_op.drop_index(batch_op.f("ix_audit_logs_conversation_id"))
    op.drop_table("audit_logs")

    with op.batch_alter_table("conversation_operator_links", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_conversation_operator_links_id"))
        batch_op.drop_index("idx_conversation_operator_active")
    op.drop_table("conversation_operator_links")
