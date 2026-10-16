"""add encrypted_additional_headers to customer_api_keys

Secret headers an api_key credential sends alongside its key, for APIs
that need two (Datadog: DD-API-KEY and DD-APPLICATION-KEY). Header name to
encrypted value; NULL is none.

Revision ID: f54cbd91b63f
Revises: dd4e5f6a7b8c
Create Date: 2026-10-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f54cbd91b63f"  # pragma: allowlist secret
down_revision: str | None = "dd4e5f6a7b8c"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customer_api_keys",
        sa.Column(
            "encrypted_additional_headers",
            sa.dialects.postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("customer_api_keys", "encrypted_additional_headers")
