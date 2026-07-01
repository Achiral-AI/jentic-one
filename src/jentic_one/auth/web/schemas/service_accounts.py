"""ServiceAccount request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

ScopeStr = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_:./-]+$")]


class ServiceAccountResponse(BaseModel):
    """ServiceAccount representation in API responses."""

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


class ServiceAccountListResponse(BaseModel):
    """List of service accounts."""

    data: list[ServiceAccountResponse]
    has_more: bool
    next_cursor: str | None = None


class ServiceAccountCreateRequest(BaseModel):
    """Request body for creating a service account."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1024)
    scopes: list[ScopeStr] | None = Field(default=None, max_length=100)


class ServiceAccountScopesRequest(BaseModel):
    """Request body for replacing a service account's scopes."""

    scopes: list[ScopeStr] = Field(max_length=100)


class ServiceAccountScopesResponse(BaseModel):
    """Response containing a service account's current scopes."""

    scopes: list[str]


class DenyRequest(BaseModel):
    """Request body for denying a service account."""

    reason: str = Field(min_length=1, max_length=1024)
