"""add curated to permission_rule_sets

``curated`` marks a shared rule set an ``org:admin`` (or a system job)
created. A curated set is attachable to a binding by any
``credentials:write`` holder and editable only by ``org:admin``; any other set
is attachable and editable by its creator or ``org:admin``. The flag is
recorded at creation, so a later change to the creator's permissions does not
change who may attach the set.

Schema only. Existing rows start as not curated; the
``rule_sets_mark_curated`` upgrade step marks the sets whose creator is a
system actor or holds ``org:admin``. It reads the admin database, so it runs
from the migration runner rather than from this Alembic tree.

Revision ID: g4d5e6f7a8b9
Revises: a9b8c7d6e5f4
Create Date: 2026-10-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "g4d5e6f7a8b9"  # pragma: allowlist secret
# Fork: reparented onto our client_options migration, which deployed
# databases already carry, so they still run this one.
down_revision: str | None = "a9b8c7d6e5f4"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "permission_rule_sets",
        sa.Column("curated", sa.Boolean, server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    # Forget the backfill along with the column, so ``migrations.run --check``
    # reports ``rule_sets_mark_curated`` pending until a full upgrade reruns it
    # on the re-added (all false) column.
    op.execute("DELETE FROM upgrade_steps WHERE name = 'rule_sets_mark_curated'")
    op.drop_column("permission_rule_sets", "curated")
