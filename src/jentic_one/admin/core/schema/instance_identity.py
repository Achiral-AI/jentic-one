"""Instance-identity ORM model.

A single-row table holding the opaque per-deployment telemetry id. The fixed
primary key (``"singleton"``) makes the seed an insert-if-absent: the replica
that wins the insert is the one that emits the once-per-instance
``instance_initialized`` event; the row's existence is the dedupe (race-safe
across replicas, no extra state). The opaque ``instance_id`` identifies nothing
about the operator — it is purely a correlation key for the ingest funnel.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from jentic_one.shared.db.base import AdminBase
from jentic_one.shared.db.types import UTCDateTime

#: The only id ever inserted — the table holds at most this one row.
INSTANCE_IDENTITY_ID = "singleton"


class InstanceIdentity(AdminBase):
    """Single-row holder of the opaque telemetry instance id (see module docstring)."""

    __tablename__ = "instance_identities"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    instance_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        UTCDateTime(),
        default=lambda: dt.datetime.now(dt.UTC),
        server_default=func.now(),
        nullable=False,
    )
