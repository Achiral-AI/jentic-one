"""IdP adapter protocol definition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class IdpClaims:
    """Normalized claims returned from an external IdP."""

    external_subject: str
    email: str
    first_name: str
    last_name: str
    email_verified: bool = False


class IdpAdapter(Protocol):
    """Protocol for pluggable external identity providers."""

    def authorize_url(self, *, state: str, nonce: str, redirect_uri: str) -> str:
        """Build the upstream authorization URL for redirecting the user."""
        ...

    async def exchange_code(self, code: str, *, redirect_uri: str) -> dict[str, object]:
        """Exchange an upstream authorization code for tokens/userinfo."""
        ...

    def map_claims(self, userinfo: dict[str, object]) -> IdpClaims:
        """Map upstream claims to the normalized IdpClaims structure."""
        ...
