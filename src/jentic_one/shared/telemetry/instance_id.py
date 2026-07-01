"""Resolve the opaque telemetry instance id (config-authoritative → admin DB).

Runs **only** when telemetry is enabled. On first startup it seeds the single
``instance_identity`` row from ``config.telemetry.instance_id`` (set at
onboarding), or generates a random opaque UUID4 if config has none. The insert is
insert-if-absent: the function returns ``(instance_id, created)`` where
``created`` is True only for the process that performed the initial insert, so
the lifecycle can emit ``instance_initialized`` exactly once.

Config is **authoritative when set**: if a config ``instance_id`` is present and
differs from the persisted row, the row is updated to match config. This keeps
the operator-visible config from silently diverging from the DB (the app never
writes config back, so config must be the source of truth). When config has no
``instance_id`` the auto-generated UUID4 is persisted and kept — there's nothing
in config to contradict it.
"""

from __future__ import annotations

import uuid

import structlog

from jentic_one.admin.core.schema.instance_identity import (
    INSTANCE_IDENTITY_ID,
    InstanceIdentity,
)
from jentic_one.shared.config import TelemetryConfig
from jentic_one.shared.db import DatabaseIntegrityError
from jentic_one.shared.db.session import DatabaseSession

logger = structlog.get_logger(__name__)


async def resolve_instance_id(
    admin_db: DatabaseSession, config: TelemetryConfig
) -> tuple[str, bool]:
    """Return ``(instance_id, created)``; ``created`` is True only on first insert."""
    seed = config.instance_id or str(uuid.uuid4())
    try:
        async with admin_db.transaction() as session:
            session.add(InstanceIdentity(id=INSTANCE_IDENTITY_ID, instance_id=seed))
        logger.info("telemetry_instance_id_created")
        return seed, True
    except DatabaseIntegrityError:
        # Another replica (or a prior startup) already seeded the row — read it.
        async with admin_db.transaction() as session:
            row = await session.get(InstanceIdentity, INSTANCE_IDENTITY_ID)
            if row is None:
                # Extremely unlikely (insert raced then vanished); fall back to the seed.
                logger.warning("telemetry_instance_id_row_missing_after_conflict")
                return seed, False
            # Config is authoritative when set: reconcile the persisted row to it so
            # config never silently diverges from the DB. Only when config *explicitly*
            # sets an id — otherwise the uuid4() fallback would clobber the durable
            # identity with a fresh random value on every boot.
            if config.instance_id and row.instance_id != config.instance_id:
                logger.warning(
                    "telemetry_instance_id_overridden_from_config",
                    previous=row.instance_id,
                    current=config.instance_id,
                )
                row.instance_id = config.instance_id
                return config.instance_id, False
            return row.instance_id, False
