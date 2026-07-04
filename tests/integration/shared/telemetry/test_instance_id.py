"""Integration tests for resolve_instance_id against real PostgreSQL.

Exercises the once-per-instance insert-if-absent semantics: the first resolve
seeds the row (created=True), and every subsequent resolve reads it back
(created=False) returning the same opaque id.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import delete

from jentic_one.admin.core.schema.instance_identity import InstanceIdentity
from jentic_one.shared.config import TelemetryConfig
from jentic_one.shared.db.session import DatabaseSession
from jentic_one.shared.telemetry.instance_id import resolve_instance_id

pytestmark = pytest.mark.integration


@pytest.fixture()
async def clean_identity(admin_db: DatabaseSession) -> AsyncGenerator[None, None]:
    async with admin_db.session() as session:
        await session.execute(delete(InstanceIdentity))
        await session.commit()
    yield
    async with admin_db.session() as session:
        await session.execute(delete(InstanceIdentity))
        await session.commit()


async def test_first_resolve_seeds_from_config(
    admin_db: DatabaseSession, clean_identity: None
) -> None:
    config = TelemetryConfig(enabled=True, instance_id="seed-from-config")

    instance_id, created = await resolve_instance_id(admin_db, config)

    assert instance_id == "seed-from-config"
    assert created is True


async def test_resolve_is_idempotent(admin_db: DatabaseSession, clean_identity: None) -> None:
    config = TelemetryConfig(enabled=True, instance_id="seed-from-config")

    first_id, first_created = await resolve_instance_id(admin_db, config)
    second_id, second_created = await resolve_instance_id(admin_db, config)

    assert first_created is True
    assert second_created is False
    assert second_id == first_id


async def test_generates_uuid_when_config_has_none(
    admin_db: DatabaseSession, clean_identity: None
) -> None:
    config = TelemetryConfig(enabled=True, instance_id=None)

    instance_id, created = await resolve_instance_id(admin_db, config)

    assert created is True
    assert instance_id  # a non-empty opaque value was generated
    # A later resolve with no config seed still returns the persisted id.
    again_id, again_created = await resolve_instance_id(admin_db, config)
    assert again_created is False
    assert again_id == instance_id


async def test_config_id_change_overrides_persisted_row(
    admin_db: DatabaseSession, clean_identity: None
) -> None:
    """Config is authoritative: changing it reconciles the persisted row."""
    seeded, created = await resolve_instance_id(
        admin_db, TelemetryConfig(enabled=True, instance_id="original")
    )
    assert created is True
    assert seeded == "original"

    changed_id, changed_created = await resolve_instance_id(
        admin_db, TelemetryConfig(enabled=True, instance_id="updated")
    )

    assert changed_created is False
    assert changed_id == "updated"
    # The override is persisted, not just returned.
    again_id, _ = await resolve_instance_id(
        admin_db, TelemetryConfig(enabled=True, instance_id="updated")
    )
    assert again_id == "updated"


async def test_empty_config_id_does_not_clobber_persisted_row(
    admin_db: DatabaseSession, clean_identity: None
) -> None:
    """A blank config id must not overwrite the durable auto-generated identity."""
    seeded, _ = await resolve_instance_id(
        admin_db, TelemetryConfig(enabled=True, instance_id="original")
    )

    kept_id, kept_created = await resolve_instance_id(
        admin_db, TelemetryConfig(enabled=True, instance_id=None)
    )

    assert kept_created is False
    assert kept_id == seeded
