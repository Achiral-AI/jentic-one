"""add instance_identity table

Revision ID: b8c9d0e1f2a3
Revises: x3y4z5a6b7c8
Create Date: 2026-06-30

Adds a single-row ``instance_identity`` table holding the opaque per-deployment
telemetry instance id. The fixed primary key (``"singleton"``) makes the seed an
insert-if-absent; the replica that wins the insert emits the once-per-instance
``instance_initialized`` event (the row is the dedupe, race-safe across replicas).
Only populated when product telemetry is enabled.

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8c9d0e1f2a3"  # pragma: allowlist secret
# OSS assembly: chain after the provider-configs head (z5a6b7c8d9e0) so the
# admin migration history stays single-headed. Originally chained onto
# x3y4z5a6b7c8, but #699's chain already extends past that revision.
down_revision: str | None = "z5a6b7c8d9e0"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "instance_identities",
        # Fixed-value PK: only the row id == "singleton" is ever inserted, so a
        # concurrent seed on a second replica trips primary-key uniqueness and the
        # loser reads the existing row instead.
        sa.Column("id", sa.String(16), nullable=False),
        sa.Column("instance_id", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("instance_identities")
