"""Access-request lifecycle enums shared across modules."""

from enum import StrEnum


class AccessRequestStatus(StrEnum):
    """Aggregate status of an access request envelope."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    PARTIALLY_APPROVED = "partially_approved"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class AccessRequestItemStatus(StrEnum):
    """Status of a single access-request line item."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
