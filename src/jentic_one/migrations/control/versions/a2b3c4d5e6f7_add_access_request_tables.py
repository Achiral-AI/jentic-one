"""add access request tables

Revision ID: a2b3c4d5e6f7
Revises: a8b9c0d1e2f3
Create Date: 2026-06-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a2b3c4d5e6f7"
down_revision: str | None = "a8b9c0d1e2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"

    op.create_table(
        "access_requests",
        sa.Column(
            "id",
            sa.String(30),
            server_default=sa.func.generate_ksuid("areq") if pg else None,
            nullable=False,
        ),
        sa.Column("actor_id", sa.String(30), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("requested_by", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("approve_url", sa.Text, nullable=False),
        sa.Column(
            "filed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("filer_owner_id", sa.String(30), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_access_requests_actor_id", "access_requests", ["actor_id"])
    op.create_index("ix_access_requests_status", "access_requests", ["status"])
    op.create_index("ix_access_requests_created_at", "access_requests", ["created_at"])
    op.create_index("ix_access_requests_created_by", "access_requests", ["created_by"])
    op.create_index("ix_access_requests_filer_owner_id", "access_requests", ["filer_owner_id"])

    op.create_table(
        "access_request_items",
        sa.Column(
            "id",
            sa.String(30),
            server_default=sa.func.generate_ksuid("arqi") if pg else None,
            nullable=False,
        ),
        sa.Column("access_request_id", sa.String(30), nullable=False),
        sa.Column("actor_id", sa.String(30), nullable=False),
        sa.Column("resource_type", sa.String(30), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column(
            "resource_reference",
            sa.dialects.postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column("to_type", sa.String(30), nullable=True),
        sa.Column("to_id", sa.String(255), nullable=True),
        sa.Column(
            "rules",
            sa.dialects.postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column(
            "applied_effects",
            sa.dialects.postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column("decided_by", sa.String(255), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(["access_request_id"], ["access_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_access_request_items_request_id",
        "access_request_items",
        ["access_request_id"],
    )
    op.create_index("ix_access_request_items_created_at", "access_request_items", ["created_at"])
    op.create_index("ix_access_request_items_created_by", "access_request_items", ["created_by"])

    if pg:
        op.create_index(
            "uq_access_request_items_pending_dedup",
            "access_request_items",
            ["actor_id", "resource_type", "action", "to_id", "resource_id"],
            unique=True,
            postgresql_where=sa.text("status = 'pending'"),
        )


def downgrade() -> None:
    pg = op.get_bind().dialect.name == "postgresql"

    if pg:
        op.drop_index("uq_access_request_items_pending_dedup", table_name="access_request_items")
    op.drop_index("ix_access_request_items_created_by", table_name="access_request_items")
    op.drop_index("ix_access_request_items_created_at", table_name="access_request_items")
    op.drop_index("ix_access_request_items_request_id", table_name="access_request_items")
    op.drop_table("access_request_items")
    op.drop_index("ix_access_requests_filer_owner_id", table_name="access_requests")
    op.drop_index("ix_access_requests_created_by", table_name="access_requests")
    op.drop_index("ix_access_requests_created_at", table_name="access_requests")
    op.drop_index("ix_access_requests_status", table_name="access_requests")
    op.drop_index("ix_access_requests_actor_id", table_name="access_requests")
    op.drop_table("access_requests")
