"""ServiceAccount service-layer view schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ServiceAccountView(BaseModel):
    """Read-model for a service account record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    owner_id: str
    registered_by: str
    approved_by: str | None = None
    status: str
    denial_reason: str | None = None
    denied_by: str | None = None
    created_at: datetime
    approved_at: datetime | None = None


class ServiceAccountCreatePayload(BaseModel):
    """Payload for creating a service account."""

    name: str
    description: str | None = None
    scopes: list[str] | None = None
