"""add client_options to oauth_client_credentials

Per-credential OAuth options for vendors that differ from the default
client: HTTP Basic token auth, a JSON token request, PKCE, a relayed
redirect URI, and token-response fields kept as server variables.

Revision ID: a9b8c7d6e5f4
Revises: f3c4d5e6a7b8
Create Date: 2026-10-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a9b8c7d6e5f4"
down_revision: str | None = "f3c4d5e6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "oauth_client_credentials",
        sa.Column(
            "client_options",
            sa.dialects.postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("oauth_client_credentials", "client_options")
