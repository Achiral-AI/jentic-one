"""apply the upstream connect revisions a fork re-parent skipped

``f54cbd91b63f`` (fork-only) first revised ``dd4e5f6a7b8c``. The upstream
merge in 488dbae9 re-parented it onto upstream's new ``e9f0a1b2c3d4``, so a
database already stamped at ``f54cbd91b63f`` reported head and never ran
``dc9d3cd8f0b7``, ``d9305dcd765e`` or ``e9f0a1b2c3d4``. This runs each of
them whose schema is missing. On an install that walked the linear chain it
changes nothing.

Downgrade changes nothing: the parent's schema includes these revisions.

Revision ID: 9f110b37d4c9
Revises: f54cbd91b63f
Create Date: 2026-11-23

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "9f110b37d4c9"  # pragma: allowlist secret
down_revision: str | None = "f54cbd91b63f"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _run(rev: str) -> None:
    # Run the revision's own upgrade() so this never drifts from upstream's DDL.
    context.script.get_revision(rev).module.upgrade()


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("connect_session_revisions"):
        _run("dc9d3cd8f0b7")  # pragma: allowlist secret
        _run("d9305dcd765e")  # pragma: allowlist secret
    columns = {c["name"] for c in inspector.get_columns("device_authorization_credentials")}
    if "flow_nonce" not in columns:
        _run("e9f0a1b2c3d4")  # pragma: allowlist secret


def downgrade() -> None:
    """No schema changes on downgrade (see the module docstring)."""
