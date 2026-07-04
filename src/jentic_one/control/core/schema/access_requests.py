"""AccessRequest ORM model — envelope for access request submissions."""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from jentic_one.shared.db.base import AuditableMixin, ControlBase
from jentic_one.shared.db.ids import generate_ksuid
from jentic_one.shared.db.types import UTCDateTime

if TYPE_CHECKING:
    from jentic_one.control.core.schema.access_request_items import AccessRequestItem


class AccessRequest(AuditableMixin, ControlBase):
    """An envelope grouping one or more access-request line items."""

    __tablename__ = "access_requests"
    __table_args__ = (Index("ix_access_requests_status", "status"),)

    id: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
        default=lambda: generate_ksuid("areq"),
        server_default=func.generate_ksuid("areq"),
    )
    actor_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    approve_url: Mapped[str] = mapped_column(Text, nullable=False)
    filed_at: Mapped[dt.datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=lambda: dt.datetime.now(dt.UTC),
        server_default=func.now(),
    )
    expires_at: Mapped[dt.datetime] = mapped_column(UTCDateTime(), nullable=False)
    filer_owner_id: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)

    created_by: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    items: Mapped[list[AccessRequestItem]] = relationship(
        back_populates="access_request",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
